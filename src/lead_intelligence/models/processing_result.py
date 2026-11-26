from dataclasses import dataclass, field

from src.lead_intelligence.models.business import Business


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

    @property
    def total_returned(self) -> int:
        return len(self.businesses)

    @property
    def total_failed(self) -> int:
        return len(self.failures)

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)
