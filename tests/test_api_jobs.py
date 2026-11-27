from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.lead_intelligence.api.app import create_app
from src.lead_intelligence.api.auth import require_user
from src.lead_intelligence.api.dependencies import get_session
from src.lead_intelligence.auth.service import Principal
from src.lead_intelligence.database.exceptions import PersistenceConflictError
from src.lead_intelligence.database.models import SearchJobRecord, SearchQueryRecord

PAYLOAD = {"country_code": "np", "city": " Kathmandu ", "query": "Travel agencies"}


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def client(session):
    app = create_app(engine_factory=lambda: MagicMock(spec=Engine))
    app.dependency_overrides[get_session] = lambda: session
    principal = Principal(uuid4(), "employee", "Employee", "employee", False)
    app.dependency_overrides[require_user] = lambda: principal
    with TestClient(app) as client:
        yield client


@pytest.fixture
def row():
    query = SearchQueryRecord(
        id=uuid4(), country_code="NP", city="Kathmandu", query="Travel agencies"
    )
    job = SearchJobRecord(
        id=uuid4(),
        query_id=query.id,
        max_results=10,
        status="completed",
        created_at=datetime(2026, 11, 27, tzinfo=UTC),
        reported_credits=2,
        unknown_credit_responses=0,
    )
    return job, query, 3, 1


def test_check_no_history(client, session):
    session.execute.return_value.first.return_value = None
    response = client.post("/api/v1/searches/check", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {
        "exists": False,
        "active_job": False,
        "refetch_allowed": False,
        "latest_job": None,
    }
    statement = session.execute.call_args.args[0]
    params = statement.compile(dialect=postgresql.dialect()).params
    assert {"NP", "kathmandu", "travel agencies"} <= {
        value for value in params.values() if isinstance(value, str)
    }
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "state", ["queued", "running", "completed", "partial", "failed", "cancelled"]
)
def test_check_history(client, session, row, state):
    row[0].status = state
    session.execute.return_value.first.return_value = row
    response = client.post("/api/v1/searches/check", json=PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is True
    assert data["active_job"] == (state in {"queued", "running"})
    assert data["refetch_allowed"] == (state not in {"queued", "running"})
    assert data["latest_job"]["result_count"] == 3


@pytest.mark.parametrize("refetch", [False, True])
def test_submit_commits_before_response(client, session, row, refetch):
    job, query, _, _ = row
    job.status = "queued"
    job.reported_credits = 0
    session.get.return_value = query
    with patch("src.lead_intelligence.api.jobs.SearchRepository") as repo:
        repo.return_value.submit.return_value = job
        response = client.post("/api/v1/jobs", json={**PAYLOAD, "refetch": refetch})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["result_count"] == 0
    assert job.created_by == client.app.dependency_overrides[require_user]().id
    request = repo.return_value.submit.call_args.args[0]
    assert request.signature == ("NP", "kathmandu", "travel agencies")
    assert repo.return_value.submit.call_args.kwargs == {"refetch": refetch}
    session.begin.return_value.__exit__.assert_called_once_with(None, None, None)


def test_conflict_rolls_back(client, session):
    with patch("src.lead_intelligence.api.jobs.SearchRepository") as repo:
        repo.return_value.submit.side_effect = PersistenceConflictError("private")
        response = client.post("/api/v1/jobs", json=PAYLOAD)
    assert response.status_code == 409
    assert response.json()["code"] == "search_conflict"
    assert "private" not in response.text
    exit_args = session.begin.return_value.__exit__.call_args.args
    assert exit_args[0] is PersistenceConflictError


@pytest.mark.parametrize(
    "overrides",
    [
        {"country_code": "ZZ"},
        {"city": " "},
        {"query": "a\nprivate"},
        {"max_results": True},
        {"max_results": 101},
        {"max_results": "10"},
        {"refetch": "true"},
        {"unexpected": "private"},
        {"city": "a" * 101},
    ],
)
def test_invalid_submission(client, session, overrides):
    response = client.post("/api/v1/jobs", json={**PAYLOAD, **overrides})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert "private" not in response.text
    session.begin.assert_not_called()


def test_history_pagination(client, session, row):
    session.execute.return_value.all.return_value = [row, row]
    response = client.get("/api/v1/jobs?limit=1&offset=2&status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["has_more"] is True
    assert data["offset"] == 2
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ORDER BY" in sql and "LIMIT" in sql and "OFFSET" in sql


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "offset=-1", "status=unknown"]
)
def test_history_validation(client, session, query):
    response = client.get(f"/api/v1/jobs?{query}")
    assert response.status_code == 422
    session.execute.assert_not_called()


def test_job_detail(client, session, row):
    session.execute.return_value.one_or_none.return_value = row
    response = client.get(f"/api/v1/jobs/{row[0].id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(row[0].id)
    assert response.json()["failure_count"] == 1


def test_job_missing(client, session):
    session.execute.return_value.one_or_none.return_value = None
    assert client.get(f"/api/v1/jobs/{uuid4()}").status_code == 404


def test_job_invalid_uuid(client, session):
    assert client.get("/api/v1/jobs/not-a-uuid").status_code == 422
    session.execute.assert_not_called()


@pytest.mark.parametrize(
    "exc, status",
    [
        (OperationalError(None, None, Exception("private")), 503),
        (SQLAlchemyError("private"), 500),
    ],
)
def test_database_error(client, session, exc, status):
    session.execute.side_effect = exc
    response = client.get("/api/v1/jobs")
    assert response.status_code == status
    assert "private" not in response.text
