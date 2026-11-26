from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PipelineProgress:
    stage: Literal["searching", "processing", "completed"]
    processed: int = 0
    total: int | None = None

    @property
    def percent(self) -> float | None:
        if self.total is None:
            return None
        if self.total == 0:
            return 100.0
        return 100.0 * self.processed / self.total
