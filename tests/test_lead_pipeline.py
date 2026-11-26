from unittest.mock import MagicMock, Mock

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.processing_result import SearchResult
from src.lead_intelligence.models.search_request import SearchRequest
from src.lead_intelligence.services.lead_pipeline import LeadPipelineService
from src.lead_intelligence.services.lead_scoring import LeadScoringService


@pytest.fixture
def request_data():
    return SearchRequest("NP", "Kathmandu", "Travel agencies")


def make_pipeline(businesses):
    search = MagicMock()
    search.__enter__.return_value = search
    search.search_request.return_value = SearchResult(businesses=businesses)
    contact = Mock()
    pipeline = LeadPipelineService(lambda: search, contact, LeadScoringService())
    return pipeline, search, contact


def test_progress_and_resource_cleanup(request_data):
    original = Business(name="Agency", country_code="US")
    pipeline, search, contact = make_pipeline([original])
    events = []
    result = pipeline.run(request_data, events.append)
    search.search_request.assert_called_once_with(request_data)
    search.__exit__.assert_called_once()
    contact.discover.assert_called_once_with(result.businesses[0], region="US")
    assert original.lead_score is None
    assert result.total_processed == result.total_scored == 1
    assert result.duration_seconds >= 0
    assert [event.stage for event in events] == [
        "searching",
        "processing",
        "processing",
        "completed",
    ]
    assert events[0].percent is None
    assert events[-1].percent == 100


def test_contact_failure_rolls_back_and_continues(request_data):
    pipeline, _, contact = make_pipeline([Business("A"), Business("B")])

    def discover(business, region):
        if business.name == "A":
            business.emails.append("bad data")
            raise RuntimeError("secret detail")
        business.extraction_status = ExtractionStatus.SUCCESS

    contact.discover.side_effect = discover
    result = pipeline.run(request_data)
    assert result.businesses[0].emails == []
    assert result.extraction_counts["failed"] == 1
    assert result.extraction_counts["success"] == 1
    assert result.total_scored == 2
    assert result.failures[0].message == "RuntimeError"
    assert result.is_partial


def test_scoring_failure_is_reported(request_data):
    pipeline, _, _ = make_pipeline([Business("A"), Business("B")])
    pipeline.scoring_service = Mock()
    pipeline.scoring_service.evaluate_business.side_effect = ValueError("bad score")
    result = pipeline.run(request_data)
    assert result.total_processed == 2
    assert result.total_scored == 0
    assert [failure.stage for failure in result.failures] == ["scoring", "scoring"]


def test_empty_search_and_callback_failure(request_data):
    pipeline, _, contact = make_pipeline([])
    callback = Mock(side_effect=RuntimeError("observer failed"))
    result = pipeline.run(request_data, callback)
    callback.assert_called_once()
    contact.discover.assert_not_called()
    assert result.total_processed == 0
    assert result.warnings
    assert not result.is_partial


def test_search_failure_propagates_and_closes(request_data):
    pipeline, search, contact = make_pipeline([])
    search.search_request.side_effect = RuntimeError("search failed")
    search.__exit__.return_value = False
    with pytest.raises(RuntimeError, match="search failed"):
        pipeline.run(request_data)
    search.__exit__.assert_called_once()
    contact.discover.assert_not_called()


def test_invalid_request_does_not_open_search():
    factory = Mock()
    with pytest.raises(TypeError, match="SearchRequest"):
        LeadPipelineService(factory).run(None)
    factory.assert_not_called()
