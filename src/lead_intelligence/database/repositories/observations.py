from datetime import UTC, datetime

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.models.common import (
    ObservationMixin,
)


def validate_observation_time(
    observed_at: datetime,
) -> datetime:
    """Validate and normalize an observation timestamp to UTC."""

    if not isinstance(observed_at, datetime):
        raise PersistenceValidationError("Observation time must be a datetime.")

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise PersistenceValidationError("Observation time must be timezone-aware.")

    return observed_at.astimezone(UTC)


def touch_observation(
    record: ObservationMixin,
    observed_at: datetime,
) -> None:
    """Refresh an observation without moving timestamps backwards."""

    observed_at = validate_observation_time(observed_at)

    if record.first_seen_at is None:
        record.first_seen_at = observed_at

    if record.last_seen_at is None:
        record.last_seen_at = max(
            record.first_seen_at,
            observed_at,
        )

    else:
        record.last_seen_at = max(
            record.first_seen_at,
            record.last_seen_at,
            observed_at,
        )
