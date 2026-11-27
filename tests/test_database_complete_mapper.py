from copy import deepcopy

import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
    complete_record_to_business,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    BusinessRecord,
    BusinessSourceRecord,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.scoring_policy import SCORING_VERSION
from src.lead_intelligence.services.lead_scoring import (
    LeadScoringService,
)


@pytest.fixture
def business():
    return Business(
        name="Example Trekking Company",
        address="Thamel, Kathmandu",
        website="https://company.com",
        category="Tour Operator",
        city="Kathmandu",
        country="Nepal",
        country_code="NP",
        emails=[
            "INFO@company.com",
            "info@company.com",
            "sales@company.com",
        ],
        phone_numbers=[
            "9846041887",
            "+9779846041887",
        ],
        source_urls=[
            "https://company.com/discovery",
        ],
        contact_page_urls=[
            "https://company.com/contact",
        ],
        email_sources={
            "info@company.com": [
                "https://company.com/contact",
            ],
        },
        phone_sources={
            "+9779846041887": [
                "https://company.com/contact",
            ],
        },
        geographic_sources={
            "city": ["provider_address"],
        },
        extraction_status=ExtractionStatus.SUCCESS,
    )


def test_complete_mapping_returns_business_record(business):
    record = business_to_complete_record(business)

    assert isinstance(record, BusinessRecord)


def test_complete_mapping_includes_contacts(business):
    record = business_to_complete_record(business)

    assert len(record.contacts) == 3

    assert all(
        isinstance(contact, BusinessContactRecord) for contact in record.contacts
    )


def test_complete_mapping_includes_sources(business):
    record = business_to_complete_record(business)

    assert len(record.sources) == 3

    assert {source.source_type for source in record.sources} == {
        "discovery",
        "website",
        "contact_page",
    }


def test_complete_mapping_preserves_contact_evidence(business):
    record = business_to_complete_record(business)

    contact = next(
        contact
        for contact in record.contacts
        if contact.normalized_value == "info@company.com"
    )

    assert [source.source_url for source in contact.sources] == [
        "https://company.com/contact",
    ]


def test_complete_round_trip_normalizes_emails(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.emails == [
        "info@company.com",
        "sales@company.com",
    ]


def test_complete_round_trip_normalizes_phones(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.phone_numbers == [
        "+9779846041887",
    ]


def test_complete_round_trip_preserves_email_sources(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.email_sources == {
        "info@company.com": [
            "https://company.com/contact",
        ],
    }


def test_complete_round_trip_preserves_phone_sources(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.phone_sources == {
        "+9779846041887": [
            "https://company.com/contact",
        ],
    }


@pytest.mark.parametrize(
    "field_name",
    [
        "name",
        "address",
        "website",
        "category",
        "city",
        "country",
        "country_code",
        "geographic_sources",
        "extraction_status",
        "source_urls",
        "contact_page_urls",
    ],
)
def test_complete_round_trip_preserves_fields(
    business,
    field_name,
):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert getattr(restored, field_name) == getattr(
        business,
        field_name,
    )


def test_complete_mapping_does_not_mutate_original(business):
    original = deepcopy(business)

    business_to_complete_record(business)

    assert business == original


def test_complete_mapping_recalculates_stale_score(business):
    business.lead_score = 1
    business.score_version = "old-policy"

    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert record.lead_score == restored.lead_score
    assert record.lead_score > 1
    assert record.score_version == SCORING_VERSION


def test_reconstruction_produces_current_score(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    scoring = LeadScoringService()

    assert scoring.is_score_current(restored)
    assert restored.score_version == SCORING_VERSION


def test_reconstruction_detects_later_score_changes(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    restored.emails.append("new@company.com")

    assert not LeadScoringService().is_score_current(
        restored,
    )


def test_reconstruction_does_not_modify_stored_score(business):
    record = business_to_complete_record(business)

    record.lead_score = 1
    record.score_version = "old-policy"

    restored = complete_record_to_business(record)

    assert restored.lead_score > 1
    assert record.lead_score == 1
    assert record.score_version == "old-policy"


def test_complete_mapping_without_contacts():
    business = Business(name="Minimal Business")

    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.emails == []
    assert restored.phone_numbers == []
    assert restored.source_urls == []
    assert restored.lead_score == 0
    assert restored.score_version == SCORING_VERSION


def test_complete_mapping_preserves_unknown_phone():
    business = Business(
        name="Example",
        phone_numbers=["unknown-phone"],
    )

    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    assert restored.phone_numbers == ["unknown-phone"]
    assert restored.lead_score == 0


def test_complete_mapping_uses_normalized_domain_fields():
    business = Business(name="Example")

    business.website = "  https://company.com  "

    record = business_to_complete_record(business)

    assert record.website == "https://company.com"

    assert record.sources[0].source_url == ("https://company.com")


def test_reconstruction_rejects_unsupported_contact(business):
    record = business_to_complete_record(business)

    record.contacts.append(
        BusinessContactRecord(
            contact_type="fax",
            value="123",
            normalized_value="123",
            sources=[],
        )
    )

    with pytest.raises(
        PersistenceValidationError,
        match="unsupported type",
    ):
        complete_record_to_business(record)


def test_reconstruction_rejects_unsupported_source(business):
    record = business_to_complete_record(business)

    record.sources.append(
        BusinessSourceRecord(
            source_type="unsupported",
            source_url="https://company.com",
        )
    )

    with pytest.raises(
        PersistenceValidationError,
        match="unsupported type",
    ):
        complete_record_to_business(record)


def test_reconstruction_metadata_is_independent(business):
    record = business_to_complete_record(business)
    restored = complete_record_to_business(record)

    restored.geographic_sources["city"].append("new-source")

    assert record.geographic_sources == {
        "city": ["provider_address"],
    }


def test_reconstruction_deduplicates_source_urls(business):
    record = business_to_complete_record(business)

    record.sources.append(
        BusinessSourceRecord(
            source_type="discovery",
            source_url="https://company.com/discovery",
        )
    )

    restored = complete_record_to_business(record)

    assert restored.source_urls == [
        "https://company.com/discovery",
    ]


@pytest.mark.parametrize("value", [None, {}, "Business"])
def test_complete_mapping_rejects_invalid_input(value):
    with pytest.raises(PersistenceValidationError):
        business_to_complete_record(value)


@pytest.mark.parametrize("value", [None, {}, "Record"])
def test_complete_reconstruction_rejects_invalid_input(value):
    with pytest.raises(PersistenceValidationError):
        complete_record_to_business(value)


def test_reconstructed_score_with_search_region():
    business = Business(
        name="Example",
        phone_numbers=["9846041887"],
    )

    record = business_to_complete_record(
        business,
        region="NP",
    )

    restored = complete_record_to_business(
        record,
        region="NP",
    )

    assert restored.lead_score == 20

    assert LeadScoringService().is_score_current(
        restored,
        region="NP",
    )


def test_search_region_normalizes_local_phone():
    business = Business(
        name="Example",
        phone_numbers=["9846041887"],
    )

    record = business_to_complete_record(
        business,
        region="NP",
    )

    assert record.country_code is None

    assert record.contacts[0].normalized_value == ("+9779846041887")


def test_business_country_overrides_search_region():
    business = Business(
        name="Example",
        country_code="NP",
        phone_numbers=["9846041887"],
    )

    record = business_to_complete_record(
        business,
        region="US",
    )

    assert record.contacts[0].normalized_value == ("+9779846041887")


def test_normalized_phone_remains_valid_without_search_region():
    business = Business(
        name="Example",
        phone_numbers=["9846041887"],
    )

    record = business_to_complete_record(
        business,
        region="NP",
    )

    restored = complete_record_to_business(record)

    assert restored.phone_numbers == [
        "+9779846041887",
    ]

    assert restored.lead_score == 20

    assert LeadScoringService().is_score_current(
        restored,
    )
