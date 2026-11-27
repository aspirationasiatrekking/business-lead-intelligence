from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
)
from src.lead_intelligence.database.mappers.sources import (
    business_to_source_records,
)
from src.lead_intelligence.database.repositories.source import (
    SourceRepository,
)
from src.lead_intelligence.models.business import Business

FIRST_SEEN = datetime(2026, 11, 25, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 11, 27, tzinfo=UTC)


@pytest.fixture
def repository():
    return SourceRepository()


@pytest.fixture
def existing():
    record = business_to_complete_record(
        Business(
            name="Example Business",
            website="https://company.com",
            contact_page_urls=[
                "https://company.com/contact",
            ],
        )
    )

    record.id = uuid4()

    for source in record.sources:
        source.id = uuid4()
        source.first_seen_at = FIRST_SEEN
        source.last_seen_at = FIRST_SEEN

    return record


def test_merge_appends_new_source(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            contact_page_urls=[
                "https://company.com/about",
            ],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.sources) == 3

    assert existing.sources[-1].source_url == ("https://company.com/about")


def test_merge_does_not_duplicate_source(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            website="https://company.com",
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.sources) == 2


def test_merge_preserves_original_source_id(
    repository,
    existing,
):
    original = existing.sources[0]
    original_id = original.id

    incoming = business_to_source_records(
        Business(
            name="Example Business",
            website="https://company.com",
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert existing.sources[0] is original
    assert existing.sources[0].id == original_id


def test_source_observation_is_refreshed(
    repository,
    existing,
):
    source = existing.sources[0]

    incoming = business_to_source_records(
        Business(
            name="Example Business",
            website="https://company.com",
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert source.first_seen_at == FIRST_SEEN
    assert source.last_seen_at == OBSERVED_AT


def test_unobserved_source_is_preserved(
    repository,
    existing,
):
    source = existing.sources[1]

    incoming = business_to_source_records(
        Business(
            name="Example Business",
            website="https://company.com",
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert source.last_seen_at == FIRST_SEEN
    assert source in existing.sources


def test_source_identity_includes_type(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            source_urls=[
                "https://company.com",
            ],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.sources) == 3

    assert {
        source.source_type
        for source in existing.sources
        if source.source_url == "https://company.com"
    } == {
        "website",
        "discovery",
    }


def test_new_source_observation_timestamps(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            source_urls=[
                "https://company.com/about",
            ],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    source = existing.sources[-1]

    assert source.first_seen_at == OBSERVED_AT
    assert source.last_seen_at == OBSERVED_AT


def test_existing_verification_status_is_preserved(
    repository,
    existing,
):
    source = existing.sources[0]
    source.verification_status = "verified"

    incoming = business_to_source_records(
        Business(
            name="Example Business",
            website="https://company.com",
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert source.verification_status == "verified"


def test_new_source_does_not_claim_verification(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            source_urls=[
                "https://company.com/about",
            ],
        )
    )

    incoming[0].verification_status = "verified"

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert existing.sources[-1].verification_status == ("unknown")


def test_source_merge_is_idempotent(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            source_urls=[
                "https://company.com/about",
            ],
        )
    )

    for _ in range(3):
        repository.merge(
            existing,
            incoming,
            observed_at=OBSERVED_AT,
        )

    assert len(existing.sources) == 3


def test_empty_source_merge_preserves_records(
    repository,
    existing,
):
    original = list(existing.sources)

    repository.merge(
        existing,
        [],
        observed_at=OBSERVED_AT,
    )

    assert list(existing.sources) == original


def test_source_merge_does_not_reuse_incoming_objects(
    repository,
    existing,
):
    incoming = business_to_source_records(
        Business(
            name="Example Business",
            source_urls=[
                "https://company.com/about",
            ],
        )
    )

    incoming[0].id = uuid4()

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert existing.sources[-1] is not incoming[0]
    assert existing.sources[-1].id is None


def test_source_merge_rejects_invalid_timestamp(
    repository,
    existing,
):
    with pytest.raises(PersistenceValidationError):
        repository.merge(
            existing,
            [],
            observed_at=None,
        )
