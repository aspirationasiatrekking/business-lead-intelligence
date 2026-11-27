"""Single-process job execution with a cooperative PostgreSQL singleton lock."""

from collections.abc import Iterator
from contextlib import contextmanager
from time import sleep
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import Connection, Engine

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.models import (
    SearchJobRecord,
    SearchQueryRecord,
    UserRecord,
)
from src.lead_intelligence.database.repositories.auth import UserRepository
from src.lead_intelligence.database.repositories.search import SearchRepository
from src.lead_intelligence.database.services.job_runner import DatabaseJobRunner
from src.lead_intelligence.models.search_request import SearchRequest

# Separate from the persistent business-deduplication transaction lock.
WORKER_LOCK = 731605220
POLL_SECONDS = 2


@contextmanager
def exclusive_worker(engine: Engine) -> Iterator[Connection]:
    """Hold a session-level lock on a dedicated autocommit connection.

    Requires a direct or session-pooled PostgreSQL connection, not transaction
    pooling. No database transaction remains open during provider requests.
    """
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        if conn.scalar(text("SELECT current_user")) != "bli_app":
            raise RuntimeError("Worker requires the runtime database role.")
        try:
            acquired = conn.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK}
            )
        except BaseException:
            # The server may have acquired the lock before the response failed.
            conn.invalidate()
            raise
        if acquired is not True:
            raise PersistenceConflictError("Another worker holds the execution lock.")
        try:
            yield conn
        finally:
            # Never return a potentially still-locked connection to the pool.
            try:
                if (
                    conn.invalidated
                    or conn.scalar(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK}
                    )
                    is not True
                ):
                    raise RuntimeError("Worker lock release could not be verified.")
            except BaseException:
                conn.invalidate()
                raise


def next_eligible_job_statement():
    return (
        select(SearchJobRecord.id)
        .join(UserRecord, SearchJobRecord.created_by == UserRecord.id)
        .where(
            SearchJobRecord.status == "queued",
            UserRecord.is_active.is_(True),
            UserRecord.must_change_password.is_(False),
        )
        .order_by(SearchJobRecord.created_at, SearchJobRecord.id)
        .limit(1)
    )


class WorkerJobRunner(DatabaseJobRunner):
    """Reuse the existing pipeline; restrict claims to active submitters."""

    def _claim(self, job_id: UUID) -> SearchRequest:
        with self.session_factory.begin() as session:
            repo = SearchRepository(session)
            original = repo.get_job(job_id)
            if original is None:
                raise RecordNotFoundError("Search job not found.")
            owner_id = original.created_by
            if original.status != "queued" or owner_id is None:
                raise PersistenceConflictError("Job is not eligible for execution.")
            # Match authentication's user-row locking order. The job state and
            # attribution are rechecked under the job lock before network I/O.
            owner = UserRepository(session).lock_by_id(owner_id)
            if owner is None or not owner.is_active or owner.must_change_password:
                raise PersistenceConflictError("Job submitter is not eligible.")
            job = repo.start(job_id)
            if job.created_by != owner_id:
                raise PersistenceConflictError("Job attribution changed.")
            query = session.get(SearchQueryRecord, job.query_id)
            if query is None:
                raise RecordNotFoundError("Search query not found.")
            return SearchRequest(
                country_code=query.country_code,
                city=query.city,
                query=query.query,
                max_results=job.max_results,
            )

    def next_job_id(self) -> UUID | None:
        with self.session_factory() as session:
            return session.scalar(next_eligible_job_statement())


def run_worker(
    engine: Engine, runner: WorkerJobRunner, *, job_id: UUID | None = None
) -> None:
    """Execute one explicit job, or poll FIFO until stopped; fail on errors."""
    with exclusive_worker(engine) as conn:
        backend_pid = conn.scalar(text("SELECT pg_backend_pid()"))
        while True:
            # Do not silently resume after losing the singleton connection.
            if (
                conn.invalidated
                or conn.scalar(text("SELECT pg_backend_pid()")) != backend_pid
            ):
                raise RuntimeError("Worker database connection was lost.")
            selected = job_id if job_id is not None else runner.next_job_id()
            if selected is not None:
                print(f"Executing job {selected}", flush=True)
                status = runner.run(selected)
                print(f"Job {selected}: {status}", flush=True)
            if job_id is not None:
                return
            # Also separate successive provider instances by at least one second.
            sleep(POLL_SECONDS)
