import os
import requests, logging
from pydantic import BaseModel, constr, field_validator, model_validator, ValidationError
from typing import List, Optional
import json
from config import get_headers, BASE_URL
import re

class Editor(BaseModel):
    object_named_as: Optional[str] = None
    scholar_id: str = "somevalue"
    series_ordinal: Optional[int] = None
    orcid_id: Optional[constr(pattern=r"^\d{4}-\d{4}-\d{4}-\d{4}$")] = None
    affiliation_string: Optional[List[str]] = None
    affiliation: Optional[List[constr(pattern=r"^Q[1-9]\d*$")]] = []
    dblp_author_id: Optional[str] = "string"
    statement_id: Optional[str] = None
        
    #Field validator to strip trailing/leading spaces (if not done, api does not accept trailing/leading spaces in the affiliation_string)
    @field_validator("object_named_as", "orcid_id", "affiliation_string", mode="before")
    @classmethod
    def strip_fields(cls, v):
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, list):
            return [s.strip() for s in v if isinstance(s, str)]
        return v
    
    #custom validator for scholar_id
    @field_validator('scholar_id')
    def validate_scholar_id(cls, v):
        if v == "somevalue":
            return v
        if not re.match(r"^Q[1-9]\d*$", v):
            raise ValueError(f"Invalid scholar_id: {v}. Must match 'Q[1-9]+' or be 'somevalue'.")
        return v
    
    #model validator to ensure affiliation_string is a list and handle the orcid
    @model_validator(mode='before')
    def convert_affiliation_string(cls, values):
        # Check if 'affiliation_string' is a string and convert it to a list with one element
        if 'affiliation_string' in values:
            if isinstance(values['affiliation_string'], str):
                values['affiliation_string'] = [values['affiliation_string']]
                
        return values
    
class Metrics(BaseModel):
    number_of_submissions: Optional[int] = None
    number_of_accepted_contributions: Optional[int] = None

headers = get_headers()

logging.basicConfig(filename='log_info.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EditorQualifierNotFoundError(Exception):
    """Custom exception for when a qualifier is not found."""
    pass

def upload_metrics(volume_qid: str, metrics: Metrics) -> None:
    
    headers = get_headers()
    
    url = f"{BASE_URL}/volumes/{volume_qid}"
    
    payload_dict = metrics.model_dump()
    
    if "number_of_accepted_contributions" in payload_dict:
        payload_dict["number_of_accepted_submissions"] = payload_dict.pop("number_of_accepted_contributions")
    
    cleaned_payload = {k: v for k, v in payload_dict.items() if v is not None}
    print(f'The cleaned_payload is {cleaned_payload}')

    # If no valid data remains, skip the upload
    if not cleaned_payload:
        print(f"[INFO] No valid metrics to upload for volume {volume_qid}. Skipping.")
        return
    
    payload = {"volume": cleaned_payload}
    
    print(f"Uploading metrics for: {volume_qid} -> {payload}")
        
    response = requests.put(url, json=payload, headers=headers)

    response.raise_for_status()
    
    return None
    

def get_editor_qualifier(volume_qid: str, editor_spec: str, headers: dict[str, str]) -> list[str]:
    try:
        url_get = f"{BASE_URL}/volumes/{volume_qid}/editors"
        response = requests.get(url_get, headers=headers)
    
        response.raise_for_status()

        editors_data = response.json()
        editors = [Editor.model_validate(editor) for editor in editors_data]

        editor_qualifier_list = [
            getattr(editor, editor_spec, None)
            for editor in editors if getattr(editor, editor_spec, None) is not None
        ]

        if not editor_qualifier_list:
            raise EditorQualifierNotFoundError(f"No {editor_spec} found for volume {volume_qid}")

        return editor_qualifier_list
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except ValidationError as val_err:
        print(f"Validation error occurred: {val_err}")
    except EditorQualifierNotFoundError as no_statID_err:
        print(f"{no_statID_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
    return []



def get_volume_qid(volume_number: str, headers: dict[str, str]) -> str:
    try:
        url_get = f"{BASE_URL}/ceur-ws/Vol-{volume_number}"
        response = requests.get(url_get, headers=headers)
        
        if response.status_code == 200:
            volume_qid_url = response.json()
            volume_qid = volume_qid_url.split('/')[-1]
            return volume_qid 
        else:
            print(f"Error getting QiD for volume {volume_number}: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return None


def upload_editor_statement(volume_qid: str, editor: Editor, headers: dict[str, str]) -> tuple[str, str]:
    
    url = f"{BASE_URL}/volumes/{volume_qid}/editors/"
    
    try:
        editor_names = get_editor_qualifier(volume_qid, "object_named_as", headers)
        
        #check if editor with same name is already uploaded
        if editor.object_named_as in editor_names:
            print(f"Editor '{editor.object_named_as}' already exists in volume {volume_qid}. Skipping.")
            return None

        payload = {"scholar_signature": editor.model_dump()}
        
        print(f"Uploading editor: {editor.object_named_as}")
        print("Payload being sent:")
        print(json.dumps(payload, indent=2))
            
        response = requests.post(url, json=payload, headers=headers)

        response.raise_for_status()
        
        try:
            response_data = response.json()
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON in upload response for editor '{editor.object_named_as}': {e}")

        statement_id = response_data.get("statement_id")
        if not statement_id:
            raise RuntimeError(f"No 'statement_id' found in response for editor '{editor.object_named_as}'")
       
        print(f"Editor '{editor.object_named_as}' successfully uploaded to volume {volume_qid}.")
        return (volume_qid, statement_id)

    except requests.exceptions.RequestException as e:
        if e.response is not None:
            print(f"Server responded with: {e.response.status_code}")
            print("Response body:")
            print(e.response.text)
        raise RuntimeError(f"Request failed while uploading editor '{editor.object_named_as}': {e}")


def check_orcid_with_orcid_api(orcid_id: str, editor: Editor) -> bool:
    '''
    Checks the validity of the orcid_id by querying the orcid API and comparing the last names.
    If the orcid_id is valid and the last names match, it returns True. Otherwise, it returns False.
    '''
    orcid_api_url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
    
    headers = {
        "Accept": "application/json"
    }

    try:
        response = requests.get(orcid_api_url, headers=headers)
        
        if response.status_code == 200:
            # ORCID ID is valid
            orcid_data = response.json()

            #extract the last name from the orcid response
            orcid_last_name = orcid_data.get('name', {}).get('family-name', {}).get('value', '').lower()
            print(orcid_last_name)

            #extract the last name from the editor data
            editor_last_name = editor.object_named_as.split()[-1].lower()  # Assuming 'object_named_as' is in the format 'First Last'
            print(editor_last_name)

            #compare the last names
            if orcid_last_name == editor_last_name:
                logging.info(f"ORCID ID {orcid_id} is valid and last names match: {editor_last_name}.")
                return True  # ORCID ID is valid and last names match
            else:
                logging.warning(f"ORCID ID {orcid_id} is valid, but last names don't match. ORCID: {orcid_last_name}, Editor: {editor_last_name}")
                return False  # ORCID ID is valid, but last names don't match
        elif response.status_code == 404:
            logging.info(f"ORCID ID {orcid_id} is not valid.")
            return False  # ORCID ID is invalid
        else:
            response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error validating ORCID ID {orcid_id}: {e}")
        return False
    
    
def clean_editor_object(editor: Editor) -> Editor:
    """
    Removes attributes from the Editor object that are None-valued,
    specifically 'orcid_id' and 'affiliation_string'.
    """
    if getattr(editor, 'orcid_id', None) is None:
        del editor.orcid_id
        print(f"[INFO] Removed 'orcid_id' for editor '{editor.object_named_as}' because it was None.")
    
    if getattr(editor, 'affiliation_string', None) is None:
        del editor.affiliation_string
        print(f"[INFO] Removed 'affiliation_string' for editor '{editor.object_named_as}' because it was None.")
    
    return editor


def load_and_upload_editors(editor: Editor, volume_number) -> tuple[str, str]:
        
    headers = get_headers()
    
    try:
        
        volume_qid = get_volume_qid(volume_number, headers)
            
        editor = clean_editor_object(editor)
        
        if hasattr(editor, "orcid_id"):
            if check_orcid_with_orcid_api(editor.orcid_id, editor):
                try:
                    volume_qid, statement_id = upload_editor_statement(volume_qid, editor, headers)
                    return (volume_qid, statement_id)
                except ValidationError as e:
                    print(f"Validation error for editor {editor.object_named_as}: {e}")
            else:
                del editor.orcid_id
                try:
                    volume_qid, statement_id = upload_editor_statement(volume_qid, editor, headers)
                    return (volume_qid, statement_id)
                except ValidationError as e:
                    print(f"Validation error for editor {editor.object_named_as}: {e}")
        else:
            try:
                volume_qid, statement_id = upload_editor_statement(volume_qid, editor, headers)
                return (volume_qid, statement_id)
            except ValidationError as e:
                print(f"Validation error for editor {editor.object_named_as}: {e}")
                
    except Exception as e:
        print(f"An unexpected error occurred: {e}")





