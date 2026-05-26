import pytest
import json
from unittest.mock import patch, mock_open
from main import main

dummy_editor_data = [
    {
        "object_named_as": "Alice",
        "scholar_id": "somevalue",
        "series_ordinal": 1,
        "affiliation_string": ["RWTH Aachen"],
        "affiliation": [],
        "dblp_author_id": "string",
        "statement_id": None
    }
]

dummy_metrics_data = {
    "number_of_submissions": 10,
    "number_of_accepted_contributions": 6
}


@patch("main.os.path.exists")
@patch("main.open", new_callable=mock_open)
def test_skips_missing_editor_file(mock_open_fn, mock_exists):
    def exists_side_effect(path):
        return False if "3000.json" in path else True
    mock_exists.side_effect = exists_side_effect

    main(3000, 3000)
    mock_open_fn.assert_not_called()


@patch("main.os.path.exists")
@patch("main.open", new_callable=mock_open)
@patch("main.load_and_upload_editors")
def test_skips_metrics_upload_if_no_volume_id(mock_upload, mock_open_fn, mock_exists):
    def exists_side_effect(path):
        return "3001.json" in path
    mock_exists.side_effect = exists_side_effect

    mock_open_fn.return_value.__enter__.return_value.read.return_value = json.dumps(dummy_editor_data)
    mock_upload.return_value = None

    main(3001, 3001)
    mock_upload.assert_called_once()


@patch("main.os.path.exists")
@patch("main.open", new_callable=mock_open)
@patch("main.load_and_upload_editors")
def test_skips_metrics_file_if_missing(mock_upload, mock_open_fn, mock_exists):
    def exists_side_effect(path):
        return "3002.json" in path and not path.endswith("_metrics.json")
    mock_exists.side_effect = exists_side_effect

    mock_open_fn.return_value.__enter__.return_value.read.return_value = json.dumps(dummy_editor_data)
    mock_upload.return_value = ("Q123", "Qabc")

    main(3002, 3002)


@patch("main.os.path.exists")
@patch("main.open", new_callable=mock_open)
@patch("main.load_and_upload_editors")
@patch("main.upload_metrics")
@patch("main.handle_affiliation_string")
def test_handles_json_file_parsing(mock_handle_aff, mock_upload_metrics, mock_upload_editors, mock_open_fn, mock_exists):
    def exists_side_effect(path):
        return True
    mock_exists.side_effect = exists_side_effect

    mock_open_fn.side_effect = [
        mock_open(read_data=json.dumps(dummy_editor_data)).return_value,
        mock_open(read_data=json.dumps(dummy_metrics_data)).return_value
    ]
    mock_upload_editors.return_value = ("Q123", "Qabc")

    main(3003, 3003)

    mock_upload_editors.assert_called_once()
    mock_upload_metrics.assert_called_once()