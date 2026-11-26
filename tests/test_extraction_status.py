import json

import pytest

from src.lead_intelligence.models.extraction_status import ExtractionStatus


def test_extraction_status_values():
    assert {status.value for status in ExtractionStatus} == {
        "pending",
        "success",
        "partial",
        "failed",
        "no_website",
        "no_contacts",
    }


def test_extraction_status_from_string():
    assert ExtractionStatus("success") is ExtractionStatus.SUCCESS


def test_extraction_status_rejects_invalid_value():
    with pytest.raises(ValueError):
        ExtractionStatus("invalid_status")


def test_extraction_status_json_serialization():
    result = json.dumps({"status": ExtractionStatus.SUCCESS})

    assert json.loads(result) == {"status": "success"}
