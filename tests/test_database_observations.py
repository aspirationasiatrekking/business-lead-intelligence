from datetime import UTC, datetime, timedelta, timezone

import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
)
from src.lead_intelligence.database.repositories.observations import (
    touch_observation,
    validate_observation_time,
)

FIRST_SEEN = datetime(2026, 11, 25, tzinfo=UTC)
LAST_SEEN = datetime(2026, 11, 26, tzinfo=UTC)
NEW_OBSERVATION = datetime(2026, 11, 27, tzinfo=UTC)


def test_validate_utc_observation():
    assert validate_observation_time(FIRST_SEEN) == FIRST_SEEN


def test_observation_is_normalized_to_utc():
    nepal_timezone = timezone(timedelta(hours=5, minutes=45))

    local_time = datetime(
        2026,
        11,
        27,
        5,
        45,
        tzinfo=nepal_timezone,
    )

    result = validate_observation_time(local_time)

    assert result == NEW_OBSERVATION
    assert result.tzinfo is UTC


@pytest.mark.parametrize(
    "value",
    [
        None,
        "2026-11-27",
        123,
        True,
    ],
)
def test_invalid_observation_types(value):
    with pytest.raises(
        PersistenceValidationError,
        match="datetime",
    ):
        validate_observation_time(value)


def test_naive_datetime_is_rejected():
    with pytest.raises(
        PersistenceValidationError,
        match="timezone-aware",
    ):
        validate_observation_time(datetime(2026, 11, 27))


def test_touch_initializes_observation():
    record = BusinessContactRecord()

    touch_observation(
        record,
        FIRST_SEEN,
    )

    assert record.first_seen_at == FIRST_SEEN
    assert record.last_seen_at == FIRST_SEEN


def test_touch_preserves_first_seen():
    record = BusinessContactRecord(
        first_seen_at=FIRST_SEEN,
        last_seen_at=LAST_SEEN,
    )

    touch_observation(
        record,
        NEW_OBSERVATION,
    )

    assert record.first_seen_at == FIRST_SEEN
    assert record.last_seen_at == NEW_OBSERVATION


def test_touch_does_not_move_last_seen_backwards():
    record = BusinessContactRecord(
        first_seen_at=FIRST_SEEN,
        last_seen_at=NEW_OBSERVATION,
    )

    touch_observation(
        record,
        LAST_SEEN,
    )

    assert record.last_seen_at == NEW_OBSERVATION


def test_touch_handles_missing_last_seen():
    record = BusinessContactRecord(
        first_seen_at=LAST_SEEN,
    )

    touch_observation(
        record,
        FIRST_SEEN,
    )

    assert record.first_seen_at == LAST_SEEN
    assert record.last_seen_at == LAST_SEEN


def test_touch_does_not_modify_verification_timestamp():
    record = BusinessContactRecord(
        first_seen_at=FIRST_SEEN,
        last_seen_at=LAST_SEEN,
        last_verified_at=FIRST_SEEN,
    )

    touch_observation(
        record,
        NEW_OBSERVATION,
    )

    assert record.last_verified_at == FIRST_SEEN
