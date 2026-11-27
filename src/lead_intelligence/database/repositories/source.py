from datetime import datetime

from src.lead_intelligence.database.models import (
    BusinessRecord,
    BusinessSourceRecord,
)
from src.lead_intelligence.database.repositories.observations import (
    touch_observation,
    validate_observation_time,
)


class SourceRepository:
    """Append-only persistence operations for business evidence."""

    @staticmethod
    def _identity(
        source: BusinessSourceRecord,
    ) -> tuple[str, str]:
        return (
            source.source_type,
            source.source_url,
        )

    def merge(
        self,
        existing: BusinessRecord,
        incoming_sources: list[BusinessSourceRecord],
        *,
        observed_at: datetime,
    ) -> None:
        """Merge validated source records into a loaded business."""

        observed_at = validate_observation_time(observed_at)

        existing_sources = {
            self._identity(source): source for source in existing.sources
        }

        for incoming in incoming_sources:
            identity = self._identity(incoming)

            source = existing_sources.get(identity)

            if source is None:
                source = BusinessSourceRecord(
                    source_type=incoming.source_type,
                    source_url=incoming.source_url,
                    verification_status="unknown",
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                )

                existing.sources.append(source)

                existing_sources[identity] = source

            else:
                touch_observation(
                    source,
                    observed_at,
                )
