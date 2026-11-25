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
