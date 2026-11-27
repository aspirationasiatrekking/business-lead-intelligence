import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.sources import (
    business_to_source_records,
)
from src.lead_intelligence.database.models import (
    BusinessSourceRecord,
)
from src.lead_intelligence.models.business import Business


def test_business_source_mapping():
    business = Business(
        name="Example Business",
        website="https://company.com",
        source_urls=[
            "https://company.com/discovery",
        ],
        contact_page_urls=[
            "https://company.com/contact",
        ],
    )

    records = business_to_source_records(business)

    assert len(records) == 3

    assert all(isinstance(record, BusinessSourceRecord) for record in records)

    assert [record.source_type for record in records] == [
        "discovery",
        "website",
        "contact_page",
    ]


def test_duplicate_business_sources_are_removed():
    business = Business(
        name="Example Business",
        source_urls=[
            "https://company.com",
            "https://company.com",
        ],
    )

    records = business_to_source_records(business)

    assert len(records) == 1


def test_same_url_with_different_types_is_preserved():
    business = Business(
        name="Example Business",
        website="https://company.com",
        source_urls=[
            "https://company.com",
        ],
        contact_page_urls=[
            "https://company.com",
        ],
    )

    records = business_to_source_records(business)

    assert len(records) == 3

    assert {record.source_type for record in records} == {
        "discovery",
        "website",
        "contact_page",
    }


def test_source_verification_status_is_unknown():
    business = Business(
        name="Example Business",
        website="https://company.com",
        website_status="verified",
    )

    records = business_to_source_records(business)

    assert records[0].verification_status == "unknown"


def test_business_without_sources():
    records = business_to_source_records(
        Business(name="Example Business"),
    )

    assert records == []


@pytest.mark.parametrize(
    "field_name",
    [
        "source_urls",
        "contact_page_urls",
    ],
)
def test_invalid_source_collection(field_name):
    business = Business(name="Example Business")

    setattr(
        business,
        field_name,
        "https://company.com",
    )

    with pytest.raises(PersistenceValidationError):
        business_to_source_records(business)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "\x00",
        "a" * 2049,
        "\ud800",
    ],
)
def test_invalid_source_values(url):
    business = Business(
        name="Example Business",
        source_urls=[url],
    )

    with pytest.raises(PersistenceValidationError):
        business_to_source_records(business)


def test_source_mapper_preserves_input():
    business = Business(
        name="Example Business",
        source_urls=[
            "https://company.com",
            "https://company.com",
        ],
    )

    business_to_source_records(business)

    assert business.source_urls == [
        "https://company.com",
        "https://company.com",
    ]


@pytest.mark.parametrize(
    "value",
    [None, {}, "Business"],
)
def test_invalid_business_input(value):
    with pytest.raises(
        PersistenceValidationError,
        match="Business instance",
    ):
        business_to_source_records(value)
