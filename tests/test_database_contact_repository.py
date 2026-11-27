from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
)
from src.lead_intelligence.database.mappers.contacts import (
    business_to_contact_records,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
)
from src.lead_intelligence.database.repositories.contact import (
    ContactRepository,
)
from src.lead_intelligence.models.business import Business

FIRST_SEEN = datetime(2026, 11, 25, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 11, 27, tzinfo=UTC)


@pytest.fixture
def repository():
    return ContactRepository()


@pytest.fixture
def existing():
    record = business_to_complete_record(
        Business(
            name="Example Business",
            country_code="NP",
            emails=["info@company.com"],
            phone_numbers=["+9779846041887"],
            email_sources={
                "info@company.com": [
                    "https://company.com/contact",
                ],
            },
        )
    )

    record.id = uuid4()

    for contact in record.contacts:
        contact.id = uuid4()
        contact.first_seen_at = FIRST_SEEN
        contact.last_seen_at = FIRST_SEEN

        for source in contact.sources:
            source.id = uuid4()
            source.first_seen_at = FIRST_SEEN
            source.last_seen_at = FIRST_SEEN

    return record


def test_merge_appends_new_contact(
    repository,
    existing,
):
    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["sales@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.contacts) == 3

    assert {contact.normalized_value for contact in existing.contacts} == {
        "info@company.com",
        "sales@company.com",
        "+9779846041887",
    }


def test_merge_does_not_duplicate_contact(
    repository,
    existing,
):
    original = existing.contacts[0]

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["INFO@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.contacts) == 2
    assert existing.contacts[0] is original


def test_merge_updates_existing_contact_timestamp(
    repository,
    existing,
):
    original = existing.contacts[0]

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert original.first_seen_at == FIRST_SEEN
    assert original.last_seen_at == OBSERVED_AT


def test_merge_preserves_unobserved_contact_timestamp(
    repository,
    existing,
):
    phone = existing.contacts[1]

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert phone.last_seen_at == FIRST_SEEN


def test_new_contact_receives_observation_timestamps(
    repository,
    existing,
):
    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["sales@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    contact = existing.contacts[-1]

    assert contact.first_seen_at == OBSERVED_AT
    assert contact.last_seen_at == OBSERVED_AT


def test_merge_preserves_existing_contact_id(
    repository,
    existing,
):
    original = existing.contacts[0]
    original_id = original.id

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert existing.contacts[0].id == original_id


def test_merge_combines_contact_evidence(
    repository,
    existing,
):
    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
            email_sources={
                "info@company.com": [
                    "https://company.com/contact",
                    "https://company.com/about",
                ],
            },
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    contact = existing.contacts[0]

    assert len(contact.sources) == 2

    assert {source.source_url for source in contact.sources} == {
        "https://company.com/contact",
        "https://company.com/about",
    }


def test_merge_refreshes_existing_source(
    repository,
    existing,
):
    source = existing.contacts[0].sources[0]

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
            email_sources={
                "info@company.com": [
                    source.source_url,
                ],
            },
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert source.first_seen_at == FIRST_SEEN
    assert source.last_seen_at == OBSERVED_AT


def test_merge_preserves_unobserved_source(
    repository,
    existing,
):
    source = existing.contacts[0].sources[0]

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert source.last_seen_at == FIRST_SEEN


def test_merge_preserves_verification_timestamp(
    repository,
    existing,
):
    contact = existing.contacts[0]
    contact.last_verified_at = FIRST_SEEN

    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["info@company.com"],
        )
    )

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert contact.last_verified_at == FIRST_SEEN


def test_merge_is_idempotent(
    repository,
    existing,
):
    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["sales@company.com"],
            email_sources={
                "sales@company.com": [
                    "https://company.com/contact",
                ],
            },
        )
    )

    for _ in range(3):
        repository.merge(
            existing,
            incoming,
            observed_at=OBSERVED_AT,
        )

    assert len(existing.contacts) == 3
    assert len(existing.contacts[-1].sources) == 1


def test_empty_merge_preserves_contacts(
    repository,
    existing,
):
    original = list(existing.contacts)

    repository.merge(
        existing,
        [],
        observed_at=OBSERVED_AT,
    )

    assert list(existing.contacts) == original


def test_merge_does_not_reuse_incoming_orm_objects(
    repository,
    existing,
):
    incoming = business_to_contact_records(
        Business(
            name="Example Business",
            emails=["sales@company.com"],
            email_sources={
                "sales@company.com": [
                    "https://company.com/contact",
                ],
            },
        )
    )

    incoming[0].id = uuid4()

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    created = existing.contacts[-1]

    assert created is not incoming[0]
    assert created.id is None
    assert created.sources[0] is not incoming[0].sources[0]


def test_contact_identity_includes_type(
    repository,
    existing,
):
    incoming = [
        BusinessContactRecord(
            contact_type="email",
            value="unknown",
            normalized_value="unknown",
            sources=[],
        ),
        BusinessContactRecord(
            contact_type="phone",
            value="unknown",
            normalized_value="unknown",
            sources=[],
        ),
    ]

    repository.merge(
        existing,
        incoming,
        observed_at=OBSERVED_AT,
    )

    assert len(existing.contacts) == 4


def test_merge_rejects_invalid_timestamp(
    repository,
    existing,
):
    with pytest.raises(PersistenceValidationError):
        repository.merge(
            existing,
            [],
            observed_at=None,
        )
