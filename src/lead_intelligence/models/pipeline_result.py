from dataclasses import dataclass, field

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.processing_result import (
    ProcessingFailure,
    SearchResult,
)
from src.lead_intelligence.models.search_request import SearchRequest


@dataclass(slots=True)
class PipelineResult:
    request: SearchRequest
    search_result: SearchResult
    businesses: list[Business] = field(default_factory=list)
    failures: list[ProcessingFailure] = field(default_factory=list)
    duration_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.businesses)

    @property
    def total_scored(self) -> int:
        return sum(b.lead_score is not None for b in self.businesses)

    @property
    def extraction_counts(self) -> dict[str, int]:
        return {
            status.value: sum(b.extraction_status == status for b in self.businesses)
            for status in ExtractionStatus
        }

    @property
    def is_partial(self) -> bool:
        return (
            self.search_result.is_partial
            or bool(self.failures)
            or any(
                b.extraction_status
                in {
                    ExtractionStatus.FAILED,
                    ExtractionStatus.PARTIAL,
                    ExtractionStatus.PENDING,
                }
                for b in self.businesses
            )
        )
