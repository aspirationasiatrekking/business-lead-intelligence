from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    PersistenceValidationError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.models import SearchQueryRecord
from src.lead_intelligence.database.repositories.search import SearchRepository
from src.lead_intelligence.database.services.persistent_deduplication import (
    PersistentDeduplicationService,
)
from src.lead_intelligence.models.pipeline_result import PipelineResult
from src.lead_intelligence.models.processing_result import ProcessingFailure
from src.lead_intelligence.models.search_request import SearchRequest
from src.lead_intelligence.services.lead_pipeline import LeadPipelineService


class DatabaseJobRunner:
    """Execute one submitted job; no database transaction during network I/O."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        pipeline: LeadPipelineService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.pipeline = pipeline if pipeline is not None else LeadPipelineService()

    def _claim(self, job_id: UUID) -> SearchRequest:
        with self.session_factory.begin() as session:
            job = SearchRepository(session).start(job_id)
            query = session.get(SearchQueryRecord, job.query_id)
            if query is None:
                raise RecordNotFoundError("Search query not found.")
            return SearchRequest(
                country_code=query.country_code,
                city=query.city,
                query=query.query,
                max_results=job.max_results,
            )

    def _save(
        self, job_id: UUID, request: SearchRequest, result: PipelineResult
    ) -> str:
        if result.request != request or len(result.businesses) > request.max_results:
            raise PersistenceValidationError("Pipeline result does not match job.")
        with self.session_factory.begin() as session:
            repo = SearchRepository(session)
            job = repo.get_job(job_id, lock=True)
            if job is None:
                raise RecordNotFoundError("Search job not found.")
            if job.status == "cancelled":
                return "cancelled"
            if job.status != "running":
                raise PersistenceConflictError("Job is not running.")

            persistence = PersistentDeduplicationService(session)
            seen = set()
            ambiguous = 0
            for observation in result.businesses:
                saved = persistence.persist(observation, region=request.phone_region)
                ambiguous += int(saved.ambiguous)
                if saved.business_id not in seen:
                    seen.add(saved.business_id)
                    repo.add_result(job_id, saved.business_id, len(seen), observation)

            search = result.search_result
            for failure in search.failures + result.failures:
                repo.add_failure(job_id, failure)

            job.reported_credits = search.reported_credits
            job.unknown_credit_responses = search.unknown_credit_responses
            job.stop_reason = search.stop_reason
            job.warnings = list(search.warnings) + list(result.warnings)
            job.search_metrics = {
                "total_discovered": search.total_discovered,
                "total_mapped": search.total_mapped,
                "duplicate_count": search.duplicate_count,
                "pages_requested": search.pages_requested,
                "pages_processed": search.pages_processed,
                "resolve_requests": search.resolve_requests,
                "website_search_requests": search.website_search_requests,
                "website_fallback_outcomes": search.website_fallback_outcomes,
                "website_candidate_outcomes": search.website_candidate_outcomes,
                "website_source_counts": search.website_source_counts,
                "total_processed": result.total_processed,
                "total_scored": result.total_scored,
                "extraction_counts": result.extraction_counts,
                "unique_persisted": len(seen),
                "ambiguous_matches": ambiguous,
                "pipeline_duration_seconds": result.duration_seconds,
            }
            if ambiguous:
                job.warnings.append("Ambiguous business identities kept separate.")
            if not seen and search.stop_reason == "provider_error":
                status = "failed"
            elif result.is_partial or ambiguous:
                status = "partial"
            else:
                status = "completed"
            # finish() refreshes the locked job: flush metrics first.
            session.flush()
            repo.finish(job_id, status)
            return status

    def _fail(self, job_id: UUID, stage: str) -> None:
        with self.session_factory.begin() as session:
            repo = SearchRepository(session)
            job = repo.get_job(job_id, lock=True)
            if job is not None and job.status == "running":
                repo.add_failure(
                    job_id,
                    ProcessingFailure(0, stage, "Job execution failed."),
                )
                job.warnings = ["Provider credit accounting may be incomplete."]
                session.flush()
                repo.finish(job_id, "failed")

    def run(self, job_id: UUID) -> str:
        request = self._claim(job_id)
        stage = "pipeline"
        try:
            result = self.pipeline.run(request)
            stage = "persistence"
            return self._save(job_id, request, result)
        except Exception:
            self._fail(job_id, stage)
            raise
