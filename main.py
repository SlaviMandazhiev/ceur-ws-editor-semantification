import os
import json
import logging

from editor_operations import load_and_upload_editors, upload_metrics, Metrics, Editor
from editor_extractor import extract_editors, extract_metrics
from affiliation_handling import handle_affiliation_string

logging.basicConfig(
    filename="main_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def main(range_start: int, range_end: int) -> None:
    for i in range(range_start, range_end + 1):
        try:
            extract_editors(i)
        except Exception as e:
            logging.error(f"Could not extract editor data from volume {i}: {e}")
            print(f"[ERROR] Could not extract editor data from volume {i} successfully")
        try:
            extract_metrics(i)
        except Exception as e:
            logging.error(f"Could not extract metrics data from volume {i}: {e}")
            print(f"[ERROR] Could not extract metrics data from volume {i} successfully")

        editor_data_file = f'{i}.json'
        metrics_data_file = f'{i}_metrics.json'
        file_path_editors = os.path.join('json_files', editor_data_file)
        file_path_metrics = os.path.join('json_files', metrics_data_file)
        
        volume_id = None
        
        if not os.path.exists(file_path_editors):
            print(f"[WARNING] Editor data file not found: {file_path_editors}, skipping volume {i}")
            continue
        
        with open(file_path_editors, 'r') as f:
            editors_data = json.load(f)
            print(f"Loaded {len(editors_data)} editor entries from '{file_path_editors}'.")
            editors_data = [Editor.model_validate(editor) for editor in editors_data]
            volume_number = editor_data_file.split('.')[0]
            
        for editor in editors_data:
            result = load_and_upload_editors(editor, volume_number)
            if result is None:
                logging.warning(f"Editor '{editor.object_named_as}' could not be uploaded for volume {volume_number}.")
                print(f"Skipping editor '{editor.object_named_as}' due to earlier error.")
                continue

            volume_id, statement_id = result

            if getattr(editor, 'affiliation_string', None) is None:
                affiliation_strings = ["null"]
            else:
                affiliation_strings = editor.affiliation_string
            
            for affiliation_string in affiliation_strings:
                
                try:
                    handle_affiliation_string(volume_id, statement_id, affiliation_string)
                except Exception as e:
                    logging.error(f"Failed to handle affiliation '{affiliation_string}' for volume {volume_id} (editor: {editor.object_named_as}): {e}")
                    print(f"[ERROR] Could not process affiliation for {volume_id}: {affiliation_string}")
                    print(f"Reason: {e}")
         
        if volume_id:           
            if not os.path.exists(file_path_metrics):
                print(f"[WARNING] Metrics data file not found: {file_path_metrics}, skipping metrics upload for volume {volume_id}")
            else:
                with open(file_path_metrics, 'r') as f:
                     metrics_data = json.load(f)
                     print(f"Loaded metrics entries from '{file_path_metrics}'.")
                     metrics_data = Metrics.model_validate(metrics_data)    
            try:
                upload_metrics(volume_id, metrics_data)
            except Exception as e:
                logging.error(f"Could not upload metrics for volume {volume_id}: {e}")
                print(f"[ERROR] Could not upload metrics for {volume_id}")
                print(f"Reason: {e}")
        else:
            print(f"[WARNING] No valid editor uploads found for volume {i}, skipping metrics upload.")
            
            
if __name__ == "__main__":
    try:
        main(3009, 3009)
    except Exception as e:
        logging.critical(f"[FATAL] Pipeline crashed: {e}")