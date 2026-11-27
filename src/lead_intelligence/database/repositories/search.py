from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    PersistenceValidationError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.models import (
    ProcessingFailureRecord,
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.database.validation import (
    validate_search_signature,
    validate_text,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import ProcessingFailure
from src.lead_intelligence.models.search_request import SearchRequest

ACTIVE = ("queued", "running")
TERMINAL = ("completed", "partial", "failed", "cancelled")


def signature_conditions(request: SearchRequest):
    country, city, query = validate_search_signature(request)
    return (
        SearchQueryRecord.country_code == country,
        SearchQueryRecord.city_normalized == city,
        SearchQueryRecord.query_normalized == query,
    )


def validate_id(value: UUID) -> None:
    if not isinstance(value, UUID):
        raise PersistenceValidationError("Record ID must be a UUID.")


class SearchRepository:
    """Search execution persistence. Caller owns the transaction."""

    def __init__(self, session: Session):
        self.session = session

    def find_query(self, request: SearchRequest) -> SearchQueryRecord | None:
        return self.session.scalar(
            select(SearchQueryRecord).where(*signature_conditions(request))
        )

    def submit(
        self, request: SearchRequest, *, refetch: bool = False
    ) -> SearchJobRecord:
        if not isinstance(refetch, bool):
            raise PersistenceValidationError("Refetch must be a boolean.")
        country, city, query = validate_search_signature(request)
        # Unique signature plus parent-row locking serializes submissions.
        self.session.execute(
            insert(SearchQueryRecord)
            .values(
                country_code=country,
                city=request.city,
                query=request.query,
                city_normalized=city,
                query_normalized=query,
            )
            .on_conflict_do_nothing(constraint="uq_search_queries_signature")
        )
        parent = self.session.execute(
            select(SearchQueryRecord)
            .where(*signature_conditions(request))
            .with_for_update()
        ).scalar_one()
        jobs = select(SearchJobRecord.id).where(SearchJobRecord.query_id == parent.id)
        if self.session.scalar(jobs.where(SearchJobRecord.status.in_(ACTIVE)).limit(1)):
            raise PersistenceConflictError("Search already has an active job.")
        if not refetch and self.session.scalar(jobs.limit(1)):
            raise PersistenceConflictError("Search already exists; confirm refetch.")
        job = SearchJobRecord(
            query_id=parent.id, max_results=request.max_results, status="queued"
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, job_id: UUID, *, lock: bool = False) -> SearchJobRecord | None:
        validate_id(job_id)
        statement = select(SearchJobRecord).where(SearchJobRecord.id == job_id)
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.session.scalar(statement)

    def _require_job(self, job_id: UUID, allowed: tuple[str, ...]) -> SearchJobRecord:
        job = self.get_job(job_id, lock=True)
        if job is None:
            raise RecordNotFoundError("Search job not found.")
        if job.status not in allowed:
            raise PersistenceConflictError("Invalid search job state.")
        return job

    def start(self, job_id: UUID) -> SearchJobRecord:
        job = self._require_job(job_id, ("queued",))
        job.status = "running"
        job.started_at = self.session.scalar(select(func.clock_timestamp()))
        self.session.flush()
        return job

    def finish(self, job_id: UUID, status: str) -> SearchJobRecord:
        if status not in TERMINAL:
            raise PersistenceValidationError("Invalid terminal status.")
        allowed = ACTIVE if status == "cancelled" else ("running",)
        job = self._require_job(job_id, allowed)
        now = self.session.scalar(select(func.clock_timestamp()))
        job.completed_at = max(now, job.started_at or job.created_at)
        if job.started_at is not None:
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        job.status = status
        self.session.flush()
        return job

    def add_result(
        self, job_id: UUID, business_id: UUID, position: int, observation: Business
    ) -> SearchResultRecord:
        validate_id(business_id)
        if not isinstance(observation, Business):
            raise PersistenceValidationError("Business observation required.")
        job = self._require_job(job_id, ("running",))
        if type(position) is not int or not 1 <= position <= job.max_results:
            raise PersistenceValidationError("Invalid result position.")
        # Duplicate canonical IDs must be collapsed by the pipeline coordinator.
        result = SearchResultRecord(
            job_id=job.id,
            business_id=business_id,
            position=position,
            extraction_status=observation.extraction_status.value,
            lead_score_at_discovery=observation.lead_score,
            score_version=observation.score_version,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def add_failure(
        self,
        job_id: UUID,
        failure: ProcessingFailure,
        *,
        business_id: UUID | None = None,
    ) -> ProcessingFailureRecord:
        if not isinstance(failure, ProcessingFailure):
            raise PersistenceValidationError("Processing failure required.")
        if (
            type(failure.item_index) is not int
            or not 0 <= failure.item_index <= 2147483647
        ):
            raise PersistenceValidationError("Invalid failure item index.")
        if business_id is not None:
            validate_id(business_id)
        validate_text(failure.stage, field_name="Failure stage")
        validate_text(failure.message, field_name="Failure message")
        validate_text(failure.item_name, field_name="Failure item name", nullable=True)
        job = self._require_job(job_id, ("running",))
        record = ProcessingFailureRecord(
            job_id=job.id,
            business_id=business_id,
            item_index=failure.item_index,
            stage=failure.stage,
            message=failure.message,
            item_name=failure.item_name,
        )
        self.session.add(record)
        self.session.flush()
        return record
