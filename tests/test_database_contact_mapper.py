import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.contacts import (
    build_contact_records,
    business_to_contact_records,
    normalize_contact_value,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    ContactSourceRecord,
)
from src.lead_intelligence.models.business import Business


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("INFO@company.com", "info@company.com"),
        ("  Sales@company.com  ", "sales@company.com"),
        ("info@company.com", "info@company.com"),
        ("unrecognized-email", "unrecognized-email"),
    ],
)
def test_email_normalization(value, expected):
    assert (
        normalize_contact_value(
            "email",
            value,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("value", "region", "expected"),
    [
        ("9846041887", "NP", "+9779846041887"),
        ("+9779846041887", None, "+9779846041887"),
        ("  not-a-phone  ", "NP", "not-a-phone"),
    ],
)
def test_phone_normalization(
    value,
    region,
    expected,
):
    assert (
        normalize_contact_value(
            "phone",
            value,
            region,
        )
        == expected
    )


def test_unsupported_contact_type():
    with pytest.raises(
        PersistenceValidationError,
        match="Unsupported contact type",
    ):
        normalize_contact_value(
            "fax",
            "123456",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "",
        " ",
        "\x00",
        "\ud800",
        "a" * 513,
    ],
)
def test_invalid_contact_values(value):
    with pytest.raises(PersistenceValidationError):
        normalize_contact_value(
            "email",
            value,
        )


def test_email_contacts_are_deduplicated():
    records = build_contact_records(
        "email",
        [
            "INFO@company.com",
            "info@company.com",
            "sales@company.com",
        ],
        {},
    )

    assert len(records) == 2

    assert records[0].value == "INFO@company.com"
    assert records[0].normalized_value == "info@company.com"


def test_equivalent_phones_are_deduplicated():
    records = build_contact_records(
        "phone",
        [
            "9846041887",
            "+9779846041887",
        ],
        {},
        region="NP",
    )

    assert len(records) == 1
    assert records[0].normalized_value == "+9779846041887"


def test_unrecognized_phone_is_preserved():
    records = build_contact_records(
        "phone",
        ["Unknown phone"],
        {},
    )

    assert len(records) == 1
    assert records[0].value == "Unknown phone"
    assert records[0].normalized_value == "Unknown phone"


def test_contact_evidence_is_combined():
    records = build_contact_records(
        "email",
        [
            "INFO@company.com",
            "info@company.com",
        ],
        {
            "INFO@company.com": [
                "https://company.com",
            ],
            "info@company.com": [
                "https://company.com",
                "https://company.com/contact",
            ],
        },
    )

    assert len(records) == 1

    assert all(isinstance(source, ContactSourceRecord) for source in records[0].sources)

    assert [source.source_url for source in records[0].sources] == [
        "https://company.com",
        "https://company.com/contact",
    ]


def test_phone_evidence_uses_normalized_identity():
    records = build_contact_records(
        "phone",
        ["9846041887"],
        {
            "+9779846041887": [
                "https://company.com/contact",
            ],
        },
        region="NP",
    )

    assert len(records[0].sources) == 1


def test_orphan_contact_evidence_is_rejected():
    with pytest.raises(
        PersistenceValidationError,
        match="no matching contact",
    ):
        build_contact_records(
            "email",
            ["info@company.com"],
            {
                "sales@company.com": [
                    "https://company.com",
                ],
            },
        )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "\x00",
        "a" * 2049,
        None,
    ],
)
def test_invalid_contact_source_urls(url):
    with pytest.raises(PersistenceValidationError):
        build_contact_records(
            "email",
            ["info@company.com"],
            {"info@company.com": [url]},
        )


def test_invalid_contact_type_rejected_when_empty():
    with pytest.raises(PersistenceValidationError):
        build_contact_records(
            "fax",
            [],
            {},
        )


def test_invalid_contact_collection():
    with pytest.raises(PersistenceValidationError):
        build_contact_records(
            "email",
            "info@company.com",
            {},
        )


def test_invalid_contact_evidence_collection():
    with pytest.raises(PersistenceValidationError):
        build_contact_records(
            "email",
            [],
            [],
        )


def test_invalid_contact_evidence_urls():
    with pytest.raises(PersistenceValidationError):
        build_contact_records(
            "email",
            ["info@company.com"],
            {
                "info@company.com": "https://company.com",
            },
        )


def test_business_contact_mapping():
    business = Business(
        name="Example Business",
        country_code="NP",
        emails=["info@company.com"],
        phone_numbers=["9846041887"],
        email_sources={
            "info@company.com": [
                "https://company.com/contact",
            ],
        },
    )

    records = business_to_contact_records(business)

    assert len(records) == 2

    assert all(isinstance(record, BusinessContactRecord) for record in records)

    assert records[0].contact_type == "email"
    assert records[1].contact_type == "phone"

    assert records[1].normalized_value == "+9779846041887"

    assert len(records[0].sources) == 1


def test_business_contact_mapping_does_not_mutate_input():
    business = Business(
        name="Example Business",
        emails=["INFO@company.com", "info@company.com"],
    )

    business_to_contact_records(business)

    assert business.emails == [
        "INFO@company.com",
        "info@company.com",
    ]


def test_business_without_contacts():
    records = business_to_contact_records(
        Business(name="Example Business"),
    )

    assert records == []


@pytest.mark.parametrize(
    "value",
    [None, {}, "Business"],
)
def test_contact_mapper_rejects_invalid_business(value):
    with pytest.raises(
        PersistenceValidationError,
        match="Business instance",
    ):
        business_to_contact_records(value)
