import pytest
from pydantic import ValidationError
from editor_operations import (
    Editor, Metrics, upload_metrics, get_editor_qualifier, get_volume_qid, clean_editor_object,
    upload_editor_statement, check_orcid_with_orcid_api, load_and_upload_editors,
    EditorQualifierNotFoundError
)
from unittest.mock import patch, Mock

#Unit tests for Editor model

def test_editor_strip_fields():
    editor = Editor(object_named_as="  Tim  ", affiliation_string=[" RWTH "])
    assert editor.object_named_as == "Tim"
    assert editor.affiliation_string == ["RWTH"]

def test_editor_orcid_validation_pass():
    editor = Editor(object_named_as="Bob", orcid_id="1234-5678-1234-5678")
    assert editor.orcid_id == "1234-5678-1234-5678"

def test_editor_orcid_validation_fail():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Bob", orcid_id="invalid-orcid")

def test_affiliation_string_conversion():
    editor = Editor(object_named_as="Alice", affiliation_string="RWTH")
    assert editor.affiliation_string == ["RWTH"]
    
def test_clean_editor_data_removes_none_affiliation():
    editor = Editor(object_named_as="Alice", affiliation_string=None)
    cleaned = clean_editor_object(editor)
    assert not hasattr(cleaned, 'affiliation_string') or cleaned.affiliation_string is None
    
def test_editor_orcid_too_short():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Invalid Orcid", orcid_id="1234-5345-5644-234", series_ordinal=1)

def test_editor_orcid_with_letter():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Invalid Orcid", orcid_id="1234-5345-5644-234X", series_ordinal=1)
        
def test_scholar_id_somevalue_valid():
    editor = Editor(object_named_as="Alice", scholar_id="somevalue", series_ordinal=1)
    assert editor.scholar_id == "somevalue"

def test_scholar_id_valid_qid():
    editor = Editor(object_named_as="Bob", scholar_id="Q123456", series_ordinal=1)
    assert editor.scholar_id == "Q123456"

def test_scholar_id_missing_q():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Charlie", scholar_id="123456", series_ordinal=1)

def test_scholar_id_with_letters():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Dave", scholar_id="QABC123", series_ordinal=1)

def test_scholar_id_just_q():
    with pytest.raises(ValidationError):
        Editor(object_named_as="Eve", scholar_id="Q", series_ordinal=1)

#Unit tests for Metrics model

def test_metrics_key_renaming():
    metrics = Metrics(number_of_submissions=12, number_of_accepted_contributions=6)
    payload = metrics.model_dump()
    if "number_of_accepted_contributions" in payload:
        payload["number_of_accepted_submissions"] = payload.pop("number_of_accepted_contributions")
    assert "number_of_accepted_submissions" in payload
    assert payload["number_of_accepted_submissions"] == 6

#Mocked tests for API calling related functions

@patch("editor_operations.requests.put")
def test_upload_metrics_skips_empty(mock_put):
    metrics = Metrics()
    upload_metrics("Q123", metrics)
    mock_put.assert_not_called()

@patch("editor_operations.requests.put")
def test_upload_metrics_valid(mock_put):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_put.return_value = mock_response

    metrics = Metrics(number_of_submissions=5)
    upload_metrics("Q123", metrics)
    mock_put.assert_called_once()

@patch("editor_operations.requests.get")
def test_get_editor_qualifier_success(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {"object_named_as": "Alice", "scholar_id": "somevalue", "series_ordinal": 1}
    ]
    mock_get.return_value = mock_response

    result = get_editor_qualifier("Q123", "object_named_as", {})
    assert result == ["Alice"]
    
@patch("editor_operations.requests.get")
def test_get_editor_qualifier_missing_qualifier(mock_get, capsys):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {"scholar_id": "somevalue", "series_ordinal": 1}
    ]
    mock_get.return_value = mock_response

    result = get_editor_qualifier("Q123", "object_named_as", {})
    captured = capsys.readouterr()
    assert "No object_named_as found for volume Q123" in captured.out
    assert result == []

@patch("editor_operations.requests.get")
def test_get_volume_qid_success(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = "http://example.com/entity/Q12345"
    mock_get.return_value = mock_response

    qid = get_volume_qid("3000", {})
    assert qid == "Q12345"

@patch("editor_operations.requests.get")
def test_check_orcid_with_orcid_api_valid(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": {"family-name": {"value": "Smith"}}
    }
    mock_get.return_value = mock_response

    editor = Editor(object_named_as="Alice Smith")
    result = check_orcid_with_orcid_api("1234-5678-1234-5678", editor)
    assert result is True

@patch("editor_operations.upload_editor_statement")
@patch("editor_operations.check_orcid_with_orcid_api")
@patch("editor_operations.get_volume_qid")
def test_load_and_upload_editors_orcid_valid(mock_qid, mock_check_orcid, mock_upload):
    mock_qid.return_value = "Q12345"
    mock_check_orcid.return_value = True
    mock_upload.return_value = ("Q12345", "Q123$abc")

    editor = Editor(object_named_as="Alice Smith", orcid_id="1234-5678-1234-5678")
    result = load_and_upload_editors(editor, "3000")
    assert result == ("Q12345", "Q123$abc")

@patch("editor_operations.upload_editor_statement")
@patch("editor_operations.get_volume_qid")
def test_load_and_upload_editors_orcid_none(mock_qid, mock_upload):
    mock_qid.return_value = "Q12345"
    mock_upload.return_value = ("Q12345", "Q123$abc")

    editor = Editor(object_named_as="Alice Smith", orcid_id=None)
    result = load_and_upload_editors(editor, "3000")
    assert result == ("Q12345", "Q123$abc")