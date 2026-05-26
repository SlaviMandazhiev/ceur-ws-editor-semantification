from langchain_core.prompts import ChatPromptTemplate
import json
from pathlib import Path
from page_extractor import Extractor
from bs4 import BeautifulSoup
from typing import Optional
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from config import get_llm

_prompt = ChatPromptTemplate.from_template(
    "Question: {question}\n\nAnswer: Let's think step by step."
)


def extract_editors(volume: int) -> str:
    '''
    Extracts certain editors' information of a CEUR-WS proceedings volume
    '''

    # html extraction

    extractor = Extractor(volume)
    html_text = extractor.get_short_html_text()
    if html_text is None:
        raise RuntimeError(f"Fetching html failed for volume {volume}")
    
    # LLM data extraction prompt

    inputs = {
  "question": f"""Here’s the CEUR-WS text:\n\"\"\"{html_text}\"\"\"\n\n Please extract each of the editor’s name,
   ordinal (the position they are in the list of editors in the text), affiliation, and ORCID as list of JSON, where
   each list entry is the information of an editor in JSON (If you couldn't find certain information write null). 

   Give me the output in this form for each editor, example:
   '
    "object_named_as": "Tim Holzheim",
    "series_ordinal": 1,
    "orcid_id": "0000-0003-2533-6363",
    "affiliation_string": "RWTH Aachen University - Lehrstuhl für Informationssysteme und Datenbanken"
    '

   Don't write anything else. I REPEAT. DON'T WRITE ANYTHING ELSE. Just give me the list of JSON, because your answer
   will automatically be inputed into another function. So don't add any extra text in your answer like 'Here are the 
   extracted editors' information' or any other notes."""
  }
    
    # invoking the LLM with the inputs
    result = (_prompt | get_llm()).invoke(inputs)

    # opening .json file to ease uploading the information in ceur-dev
    
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        raise ValueError(f"LLM output was not valid JSON for volume {volume}")

    # get the directory containing this script
    cwd = Path(__file__).resolve().parent

    # build a subfolder path “json_files” and ensure it exists
    output_dir = cwd / "json_files"
    output_dir.mkdir(parents=True, exist_ok=True)

    # build the full file path in a cross-platform way
    output_path = output_dir / f"{volume}.json"

    # write out the JSON
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return result 

def extract_metrics(volume: int) -> str:
    '''
    Extracts the number of submissions and number of accepted contributions of a CEUR-WS proceedings volume
    '''

    # html extraction
    
    extractor = Extractor(volume)
    raw_html = extractor.html
    html_text = extractor.get_short_html_text()   
    if html_text is None:
        raise RuntimeError(f"Fetching html failed for volume {volume}")

    soup = BeautifulSoup(raw_html, "html.parser")
    html_text = soup.get_text(separator = "")
    
    # LLM metrics extraction prompt

    inputs = {
        "question": f"""\n\"\"\"{html_text}\"\"\"\n\n Give me the number of papers submitted and the number of them that were accepted. 
        in the form of JSON dictionary:
        
        
        "number_of_submissions": <number>,
        "number_of_accepted_contributions": <number>
        
        
        Where "number of submissions" and "number of accepted contributions" are strings and <number> is an integer.
        
        Give only one key-value pair for both submissions and contributions. The dictionary should have only 2 entries.
        
        If not found write null after the semicolons. 

        Give me the response in that form and don't write anything else. I REPEAT. DON'T WRITE ANYTHING ELSE. Just give me the answer in the
        form of JSON, because your answer will automatically be inputed into another function. So don't add any extra text in your answer like 
        'Here is the extracted information' or anything similar."""
    }
    
    # invoking LLM
    result = (_prompt | get_llm()).invoke(inputs)

    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        raise ValueError(f"LLM output was not valid JSON for volume {volume}")
    
    
    cwd = Path(__file__).resolve().parent

    # build a subfolder path “json_files” and ensure it exists
    output_dir = cwd / "json_files"
    output_dir.mkdir(parents=True, exist_ok=True)

    # build the full file path in a cross-platform way
    output_path = output_dir / f"{volume}_metrics.json"

    # write out the JSON
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return result

# testing part
    
def are_names_present(volume: int) -> bool:
    '''
    Checks if the editors' names extracted by the LLM are in the html text to ensure no hallucinations
    '''
    
    # extract names from LLM json response and put them in a dict

    editors_json = extract_editors(volume)
    if editors_json != None:
        editors_dicts = json.loads(editors_json)
    else:
        print("No editor extracted by the LLM")
        return False

    # get whole html text, get editors' names from LLM extraction, and check if the editors' names are in the html text

    html_text = Extractor(volume).get_short_html_text()
    editors_names = []
    for dictionary in editors_dicts:
        editors_names.append(dictionary.get("object_named_as"))
   
    if None in editors_names:
        print("No editor was extracted by the LLM")    
        return False
    
    for name in editors_names:
        if name not in html_text:
            return False 
    return True 

def get_number_of_creators(volume: int) -> Optional[int]:
    '''
    Return the dblp:numberOfCreators value for a CEUR-WS volume,
    or None if the volume is missing from the KG.
    '''

    # dblp endpoint and sparql setup, namely JSON format, making HTTP requests with POST, and setting a timeout of 60 seconds for a response

    endpoint = "https://sparql.dblp.org/sparql"  
    sparql = SPARQLWrapper(endpoint, agent="dblp-client/1.0")
    sparql.setReturnFormat(JSON)
    sparql.setMethod(POST)            
    sparql.setTimeout(60)

    # sparql code

    query = f"""
    PREFIX dblp: <https://dblp.org/rdf/schema#>

    SELECT ?numCreators
    WHERE {{
      VALUES ?volume_number {{ "{volume}" }}
      ?volume dblp:publishedInSeries       "CEUR Workshop Proceedings" ;
              dblp:publishedInSeriesVolume ?volume_number ;
              dblp:numberOfCreators        ?numCreators .
    }}
    LIMIT 1
    """

    # setting the above query and making the query

    sparql.setQuery(query)
    results = sparql.query().convert().get("results", {}).get("bindings", [])

    # if the volume doesn't exist in the dblp database return None

    if not results:
        return None                           
    return int(results[0]["numCreators"]["value"])



