from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.services.worker import (
    WorkerJobRunner,
    exclusive_worker,
    next_eligible_job_statement,
    run_worker,
)

MODULE = "src.lead_intelligence.database.services.worker"


@pytest.fixture
def connection():
    engine = MagicMock()
    context = engine.connect.return_value.execution_options.return_value
    conn = context.__enter__.return_value
    conn.invalidated = False
    return engine, conn


def test_lock_acquisition_and_release(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, True]
    with exclusive_worker(engine) as locked:
        assert locked is conn
    assert "pg_try_advisory_lock" in str(conn.scalar.call_args_list[1].args[0])
    assert "pg_advisory_unlock" in str(conn.scalar.call_args_list[2].args[0])


def test_wrong_role(connection):
    engine, conn = connection
    conn.scalar.return_value = "bli_migrator"
    with pytest.raises(RuntimeError), exclusive_worker(engine):
        pytest.fail("Wrong role accepted")
    assert conn.scalar.call_count == 1


def test_competing_worker_rejected(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", False]
    with pytest.raises(PersistenceConflictError), exclusive_worker(engine):
        pytest.fail("Second worker accepted")
    assert conn.scalar.call_count == 2


def test_unlock_on_exception(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, True]
    with pytest.raises(ValueError), exclusive_worker(engine):
        raise ValueError("test")
    assert conn.scalar.call_count == 3


@pytest.mark.parametrize("failure", [False, RuntimeError("disconnect")])
def test_failed_unlock_invalidates(connection, failure):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, failure]
    with pytest.raises(RuntimeError), exclusive_worker(engine):
        pass
    conn.invalidate.assert_called_once()


def test_queue_sql():
    sql = str(next_eligible_job_statement().compile(dialect=postgresql.dialect()))
    assert "JOIN lead_intelligence.users" in sql
    assert "created_by" in sql
    assert "is_active IS true" in sql
    assert "must_change_password IS false" in sql
    assert "ORDER BY" in sql and "LIMIT" in sql


@pytest.fixture
def claim():
    factory = MagicMock()
    session = factory.begin.return_value.__enter__.return_value
    runner = WorkerJobRunner(factory, pipeline=MagicMock())
    job_id, owner_id, query_id = uuid4(), uuid4(), uuid4()
    with (
        patch(f"{MODULE}.SearchRepository") as searches,
        patch(f"{MODULE}.UserRepository") as users,
    ):
        repo, user_repo = searches.return_value, users.return_value
        record = SimpleNamespace(
            status="queued", created_by=owner_id, query_id=query_id, max_results=3
        )
        repo.get_job.return_value = record
        repo.start.return_value = record
        user_repo.lock_by_id.return_value = SimpleNamespace(
            is_active=True, must_change_password=False
        )
        session.get.return_value = SimpleNamespace(
            country_code="NP", city="Kathmandu", query="Travel agencies"
        )
        yield runner, job_id, repo, user_repo, session


def test_claim_valid_job(claim):
    runner, job_id, repo, users, _ = claim
    request = runner._claim(job_id)
    assert request.country_code == "NP" and request.max_results == 3
    users.lock_by_id.assert_called_once_with(repo.get_job.return_value.created_by)
    repo.start.assert_called_once_with(job_id)


def test_missing_job(claim):
    runner, job_id, repo, _, _ = claim
    repo.get_job.return_value = None
    with pytest.raises(RecordNotFoundError):
        runner._claim(job_id)
    repo.start.assert_not_called()


@pytest.mark.parametrize("status,owner", [("queued", None), ("running", uuid4())])
def test_unclaimable_job(claim, status, owner):
    runner, job_id, repo, users, _ = claim
    repo.get_job.return_value.status = status
    repo.get_job.return_value.created_by = owner
    with pytest.raises(PersistenceConflictError):
        runner._claim(job_id)
    users.lock_by_id.assert_not_called()
    repo.start.assert_not_called()


@pytest.mark.parametrize("active,temporary", [(False, False), (True, True)])
def test_ineligible_owner(claim, active, temporary):
    runner, job_id, repo, users, _ = claim
    users.lock_by_id.return_value.is_active = active
    users.lock_by_id.return_value.must_change_password = temporary
    with pytest.raises(PersistenceConflictError):
        runner._claim(job_id)
    repo.start.assert_not_called()


def test_changed_attribution(claim):
    runner, job_id, repo, _, _ = claim
    repo.start.return_value = SimpleNamespace(created_by=uuid4())
    with pytest.raises(PersistenceConflictError):
        runner._claim(job_id)


def test_explicit_job_only(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, 42, 42, True]
    runner = MagicMock()
    job_id = uuid4()
    run_worker(engine, runner, job_id=job_id)
    runner.run.assert_called_once_with(job_id)
    runner.next_job_id.assert_not_called()


def test_lost_lock_stops_before_run(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, 42, 43, True]
    runner = MagicMock()
    with pytest.raises(RuntimeError):
        run_worker(engine, runner, job_id=uuid4())
    runner.run.assert_not_called()


def test_worker_does_not_retry_failed_job(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, 42, 42, True]
    runner = MagicMock()
    runner.run.side_effect = RuntimeError("pipeline failed")
    with pytest.raises(RuntimeError):
        run_worker(engine, runner, job_id=uuid4())
    assert runner.run.call_count == 1


def test_poll_waits_when_no_job(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", True, 42, 42, True]
    runner = MagicMock()
    runner.next_job_id.return_value = None
    with patch(f"{MODULE}.sleep", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            run_worker(engine, runner)
    runner.next_job_id.assert_called_once()
    runner.run.assert_not_called()


def test_uncertain_lock_acquisition_invalidates(connection):
    engine, conn = connection
    conn.scalar.side_effect = ["bli_app", RuntimeError("disconnect")]
    with pytest.raises(RuntimeError), exclusive_worker(engine):
        pass
    conn.invalidate.assert_called_once()
