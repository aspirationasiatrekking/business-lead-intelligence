from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.lead_intelligence.database.exceptions import PersistenceValidationError
from src.lead_intelligence.database.models import SearchJobRecord, SearchQueryRecord
from src.lead_intelligence.database.services.job_runner import DatabaseJobRunner
from src.lead_intelligence.database.services.persistent_deduplication import (
    PersistenceResult,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.pipeline_result import PipelineResult
from src.lead_intelligence.models.processing_result import SearchResult
from src.lead_intelligence.models.search_request import SearchRequest

MODULE = "src.lead_intelligence.database.services.job_runner"


@pytest.fixture
def setup():
    factory = MagicMock()
    session = factory.begin.return_value.__enter__.return_value
    pipeline = MagicMock()
    runner = DatabaseJobRunner(factory, pipeline)
    request = SearchRequest(country_code="NP", city="Kathmandu", query="Trekking")
    return runner, session, pipeline, request


def test_claim_builds_request(setup):
    runner, session, _, request = setup
    job = SearchJobRecord(id=uuid4(), query_id=uuid4(), max_results=10)
    session.get.return_value = SearchQueryRecord(
        country_code="NP", city="Kathmandu", query="Trekking"
    )
    with patch(f"{MODULE}.SearchRepository") as repository:
        repository.return_value.start.return_value = job
        assert runner._claim(job.id) == request
        repository.return_value.start.assert_called_once_with(job.id)


def test_run_claims_before_network_and_saves(setup):
    runner, _, pipeline, request = setup
    result = PipelineResult(request, SearchResult())
    pipeline.run.return_value = result
    job_id = uuid4()
    with (
        patch.object(runner, "_claim", return_value=request),
        patch.object(runner, "_save", return_value="completed") as save,
    ):
        assert runner.run(job_id) == "completed"
    pipeline.run.assert_called_once_with(request)
    save.assert_called_once_with(job_id, request, result)


def test_failed_pipeline_marks_job(setup):
    runner, _, pipeline, request = setup
    pipeline.run.side_effect = RuntimeError("secret detail")
    job_id = uuid4()
    with (
        patch.object(runner, "_claim", return_value=request),
        patch.object(runner, "_fail") as fail,
        pytest.raises(RuntimeError),
    ):
        runner.run(job_id)
    fail.assert_called_once_with(job_id, "pipeline")


def test_save_collapses_canonical_ids(setup):
    runner, _, _, request = setup
    job_id, business_id = uuid4(), uuid4()
    observations = [Business(name="A"), Business(name="B")]
    result = PipelineResult(
        request, SearchResult(reported_credits=3), businesses=observations
    )
    job = SearchJobRecord(id=job_id, status="running")
    with (
        patch(f"{MODULE}.SearchRepository") as repository,
        patch(f"{MODULE}.PersistentDeduplicationService") as service,
    ):
        repo = repository.return_value
        repo.get_job.return_value = job
        service.return_value.persist.return_value = PersistenceResult(
            business_id, False
        )
        assert runner._save(job_id, request, result) == "partial"
        repo.add_result.assert_called_once_with(job_id, business_id, 1, observations[0])
        repo.finish.assert_called_once_with(job_id, "partial")
    assert job.reported_credits == 3
    assert job.search_metrics["unique_persisted"] == 1


def test_cancelled_job_discards_results(setup):
    runner, _, _, request = setup
    with (
        patch(f"{MODULE}.SearchRepository") as repository,
        patch(f"{MODULE}.PersistentDeduplicationService") as service,
    ):
        repository.return_value.get_job.return_value = SearchJobRecord(
            status="cancelled"
        )
        assert (
            runner._save(uuid4(), request, PipelineResult(request, SearchResult()))
            == "cancelled"
        )
        service.assert_not_called()


def test_mismatched_request_rejected(setup):
    runner, _, _, request = setup
    other = SearchRequest(country_code="US", city="Boston", query="Travel")
    with pytest.raises(PersistenceValidationError):
        runner._save(uuid4(), request, PipelineResult(other, SearchResult()))
