import requests
from config import BASE_URL, IMPORT_URL, get_headers, get_llm

WIKIDATA_REST = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
    
    
def handle_affiliation_string(volume_id: str, statement_id: str, affiliation_string: str) -> None:
    headers = get_headers()

    affiliation = extract_affiliation(affiliation_string)
    wd_id = get_wikidata_id(affiliation)
    if not check_instance_of(wd_id):
        raise RuntimeError("The extracted affiliation seems to be wrong!")
        
    print(f'Wikidata ID is{wd_id}')
    cd_id = import_affiliation(wd_id, headers)
    print(f'the payload is: {cd_id}')
    affiliations = [cd_id]
    print(affiliations)
    update_editor_signature(volume_id, statement_id, affiliations, headers)


def extract_affiliation(affiliation_string: str) -> str:
    prompt = (
        "Extract only the main organization name (e.g., university or company) "
        "from the following affiliation string. Do not include department names "
        "or other sub-units. Return only the name, with no extra words or "
        "punctuation.\n"
        f"Affiliation: {affiliation_string}\n"
        "Main organization:"
    )

    return get_llm().invoke(prompt)


def get_wikidata_id(entity_name: str) -> str:
    params = {"action": "wbsearchentities", "search": entity_name, "language": "en", "format": "json"}

    response = requests.get(WIKIDATA_REST, params=params)
    response.raise_for_status()

    data = response.json()
    if data["search"] is not None and len(data["search"]) != 0:
        return data["search"][0]["id"]
    else:
        raise RuntimeError("No wikidata entry found!")


def check_instance_of(wikidata_id: str) -> bool:
    query = f"""SELECT ?instanceOfLabel WHERE {{
                    wd:{wikidata_id} wdt:P31 ?instanceOf.
                    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}"""
    headers = {"Accept": "application/sparql-results+json"}

    response = requests.get(WIKIDATA_SPARQL, params={"query": query}, headers=headers)
    response.raise_for_status()
    results = response.json()["results"]["bindings"]
    labels = [result["instanceOfLabel"]["value"] for result in results]

    # todo: add more thorough testing
    return any("institute" in label.lower() or "university" in label.lower() or "research" in label.lower() for label in labels)


def import_affiliation(wd_id: str, headers: dict[str, str]) -> str:
    response = requests.post(IMPORT_URL + wd_id, headers=headers)
    response.raise_for_status()

    return response.json().get("ceurdev_id") 


def update_editor_signature(
    volume_id: str, statement_id: str, affiliations: list[str], headers: dict[str, str]
) -> None:
    url = f"{BASE_URL}/volumes/{volume_id}/editors/{statement_id}"
    body = {"scholar_signature": {"affiliation": affiliations}}

    response = requests.put(url, json=body, headers=headers)
    response.raise_for_status()


        
