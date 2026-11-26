from dataclasses import dataclass, field

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.search_request import SearchRequest


@dataclass
class ProcessingFailure:
    item_index: int
    stage: str
    message: str
    item_name: str | None = None


@dataclass
class MappingResult:
    businesses: list[Business] = field(default_factory=list)
    failures: list[ProcessingFailure] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.businesses) + len(self.failures)


@dataclass
class SearchResult:
    businesses: list[Business] = field(default_factory=list)

    failures: list[ProcessingFailure] = field(default_factory=list)

    total_discovered: int = 0
    total_mapped: int = 0
    duplicate_count: int = 0

    request: SearchRequest | None = None

    pages_requested: int = 0
    pages_processed: int = 0

    resolve_requests: int = 0

    reported_credits: int = 0
    unknown_credit_responses: int = 0

    warnings: list[str] = field(default_factory=list)

    stop_reason: str | None = None

    @property
    def total_returned(self) -> int:
        return len(self.businesses)

    @property
    def total_failed(self) -> int:
        return len(self.failures)

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

    @property
    def is_partial(self) -> bool:
        return self.stop_reason in {
            "provider_error",
            "page_budget_reached",
            "no_progress",
        } or bool(self.warnings)

    @property
    def credit_tracking_complete(self) -> bool:
        return self.unknown_credit_responses == 0
