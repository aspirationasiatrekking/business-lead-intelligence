from collections.abc import Callable
from copy import deepcopy
from time import monotonic

from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.pipeline_progress import PipelineProgress
from src.lead_intelligence.models.pipeline_result import PipelineResult
from src.lead_intelligence.models.processing_result import ProcessingFailure
from src.lead_intelligence.models.search_request import SearchRequest
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.services.lead_scoring import LeadScoringService


class LeadPipelineService:
    """Synchronous orchestration; owns each search service created by its factory."""

    def __init__(
        self,
        search_factory: Callable[[], BusinessSearchService] = BusinessSearchService,
        contact_service: ContactDiscoveryService | None = None,
        scoring_service: LeadScoringService | None = None,
    ) -> None:
        self.search_factory = search_factory
        self.contact_service = (
            contact_service
            if contact_service is not None
            else ContactDiscoveryService()
        )
        self.scoring_service = (
            scoring_service if scoring_service is not None else LeadScoringService()
        )

    def run(
        self,
        request: SearchRequest,
        on_progress: Callable[[PipelineProgress], None] | None = None,
    ) -> PipelineResult:
        if not isinstance(request, SearchRequest):
            raise TypeError("Expected a SearchRequest instance")
        started = monotonic()
        warnings: list[str] = []

        def emit(event: PipelineProgress) -> None:
            nonlocal on_progress
            if on_progress is not None:
                try:
                    on_progress(event)
                except Exception as exc:
                    # A broken observer must not discard discovered leads.
                    warnings.append(f"Progress callback failed ({type(exc).__name__})")
                    on_progress = None

        emit(PipelineProgress("searching"))
        with self.search_factory() as search:
            search_result = search.search_request(request)
        result = PipelineResult(request, search_result, warnings=warnings)
        total = search_result.total_returned
        emit(PipelineProgress("processing", 0, total))
        for index, original in enumerate(search_result.businesses):
            business = deepcopy(original)
            region = business.country_code or request.phone_region
            try:
                self.contact_service.discover(business, region=region)
            except Exception as exc:
                # Roll back partially mutated contact data on unexpected errors.
                business = deepcopy(original)
                business.extraction_status = ExtractionStatus.FAILED
                business.contact_page_urls = []
                business.invalidate_score()
                result.failures.append(
                    ProcessingFailure(
                        index, "contact_discovery", type(exc).__name__, original.name
                    )
                )
            try:
                self.scoring_service.evaluate_business(business, region=region)
            except Exception as exc:
                business.invalidate_score()
                result.failures.append(
                    ProcessingFailure(
                        index, "scoring", type(exc).__name__, original.name
                    )
                )
            result.businesses.append(business)
            emit(PipelineProgress("processing", index + 1, total))
        emit(PipelineProgress("completed", total, total))
        result.duration_seconds = monotonic() - started
        return result
