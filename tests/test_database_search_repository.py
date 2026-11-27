from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    PersistenceValidationError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.models import SearchJobRecord, SearchQueryRecord
from src.lead_intelligence.database.repositories.search import SearchRepository
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import ProcessingFailure
from src.lead_intelligence.models.search_request import SearchRequest


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def repo(session):
    return SearchRepository(session)


@pytest.fixture
def request_data():
    return SearchRequest(country_code="NP", city="Kathmandu", query="Trekking")


@pytest.fixture
def job():
    return SearchJobRecord(
        id=uuid4(),
        max_results=10,
        status="running",
        created_at=datetime(2026, 11, 27, tzinfo=UTC),
        started_at=datetime(2026, 11, 27, tzinfo=UTC),
    )


def test_find_query(repo, session, request_data):
    repo.find_query(request_data)
    compiled = session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert {"NP", "kathmandu", "trekking"} <= set(compiled.params.values())


@pytest.mark.parametrize("refetch", [False, True])
def test_submit(repo, session, request_data, refetch):
    parent = SearchQueryRecord(id=uuid4())
    session.execute.return_value.scalar_one.return_value = parent
    session.scalar.return_value = None
    result = repo.submit(request_data, refetch=refetch)
    assert result.query_id == parent.id
    assert result.status == "queued"
    assert result.max_results == 10
    assert "ON CONFLICT" in str(session.execute.call_args_list[0].args[0])
    assert "FOR UPDATE" in str(session.execute.call_args_list[1].args[0])
    session.commit.assert_not_called()


@pytest.mark.parametrize("refetch", [False, True])
def test_active_conflict(repo, session, request_data, refetch):
    session.scalar.return_value = uuid4()
    with pytest.raises(PersistenceConflictError, match="active"):
        repo.submit(request_data, refetch=refetch)
    session.add.assert_not_called()


def test_duplicate_requires_refetch(repo, session, request_data):
    session.scalar.side_effect = [None, uuid4()]
    with pytest.raises(PersistenceConflictError, match="refetch"):
        repo.submit(request_data)


def test_invalid_refetch(repo, request_data):
    with pytest.raises(PersistenceValidationError):
        repo.submit(request_data, refetch=1)


def test_start(repo, session, job):
    job.status = "queued"
    session.scalar.side_effect = [job, job.created_at]
    assert repo.start(job.id).status == "running"
    assert job.started_at == job.created_at
    session.commit.assert_not_called()


def test_start_missing(repo, session):
    session.scalar.return_value = None
    with pytest.raises(RecordNotFoundError):
        repo.start(uuid4())


def test_start_running_conflict(repo, session, job):
    session.scalar.return_value = job
    with pytest.raises(PersistenceConflictError):
        repo.start(job.id)


@pytest.mark.parametrize("status", ["completed", "partial", "failed", "cancelled"])
def test_finish(repo, session, job, status):
    session.scalar.side_effect = [job, job.started_at]
    assert repo.finish(job.id, status).status == status
    assert job.duration_seconds == 0
    session.commit.assert_not_called()


def test_invalid_terminal_status(repo, job):
    with pytest.raises(PersistenceValidationError):
        repo.finish(job.id, "running")


def test_add_result(repo, session, job):
    session.scalar.return_value = job
    business_id = uuid4()
    result = repo.add_result(job.id, business_id, 1, Business(name="Example"))
    assert result.business_id == business_id
    assert result.position == 1
    assert result.extraction_status == "pending"
    session.flush.assert_called_once()


@pytest.mark.parametrize("position", [0, 11, True])
def test_invalid_position(repo, session, job, position):
    session.scalar.return_value = job
    with pytest.raises(PersistenceValidationError):
        repo.add_result(job.id, uuid4(), position, Business(name="Example"))


def test_add_failure(repo, session, job):
    session.scalar.return_value = job
    result = repo.add_failure(job.id, ProcessingFailure(0, "mapping", "Invalid data"))
    assert result.job_id == job.id
    assert result.stage == "mapping"
    session.commit.assert_not_called()


def test_invalid_failure(repo, job):
    with pytest.raises(PersistenceValidationError):
        repo.add_failure(job.id, ProcessingFailure(-1, "mapping", "Invalid data"))
