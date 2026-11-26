import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)


def test_deduplicate_businesses_by_website_domain():
    businesses = [
        Business(
            name="Nepal Hiking Team",
            website="https://www.example.com/",
        ),
        Business(
            name="Nepal Hiking Team Pvt Ltd",
            website="https://example.com/about",
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 1


def test_deduplicate_businesses_by_phone_number():
    businesses = [
        Business(
            name="Business One",
            phone_numbers=["+9779846041887"],
        ),
        Business(
            name="Business Two",
            phone_numbers=["+9779846041887"],
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 1


def test_deduplicate_businesses_by_name_and_address():
    businesses = [
        Business(
            name="ABC Adventures",
            address="Thamel, Kathmandu, Nepal",
        ),
        Business(
            name="abc adventures",
            address="Thamel, Kathmandu, Nepal",
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 1


def test_do_not_merge_businesses_by_name_alone():
    businesses = [
        Business(
            name="ABC Adventures",
            address="Kathmandu, Nepal",
        ),
        Business(
            name="ABC Adventures",
            address="Pokhara, Nepal",
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 2


def test_merge_contact_information_from_duplicates():
    businesses = [
        Business(
            name="Example Business",
            website="https://example.com",
            emails=["info@example.com"],
            phone_numbers=["+9779846041887"],
        ),
        Business(
            name="Example Business",
            website="https://www.example.com",
            emails=["sales@example.com"],
            phone_numbers=["+9779846041887"],
            category="Adventure Travel",
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 1
    assert result[0].emails == [
        "info@example.com",
        "sales@example.com",
    ]
    assert result[0].phone_numbers == ["+9779846041887"]
    assert result[0].category == "Adventure Travel"


def test_do_not_merge_different_domains_even_if_phone_matches():
    businesses = [
        Business(
            name="Company A",
            website="https://company-a.com",
            phone_numbers=["+9779846041887"],
        ),
        Business(
            name="Company B",
            website="https://company-b.com",
            phone_numbers=["+9779846041887"],
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 2


def test_do_not_merge_different_names_when_domains_conflict():
    first = Business(
        name="Company A",
        website="https://company-a.com",
    )

    second = Business(
        name="Company B",
        website="https://company-b.com",
    )

    service = BusinessDeduplicationService()

    assert service.are_duplicates(first, second) is False


def test_do_not_merge_businesses_with_empty_normalized_phone():
    businesses = [
        Business(
            name="Company A",
            phone_numbers=["abc"],
        ),
        Business(
            name="Company B",
            phone_numbers=["xyz"],
        ),
    ]

    service = BusinessDeduplicationService()
    result = service.deduplicate(businesses)

    assert len(result) == 2


@pytest.mark.parametrize(
    ("website", "expected"),
    [
        ("https://example.com", "example.com"),
        ("https://www.example.com/", "example.com"),
        ("HTTPS://EXAMPLE.COM/about", "example.com"),
        ("http://example.com/contact", "example.com"),
        (None, None),
        ("", None),
        ("invalid-url", None),
        ("ftp://example.com", None),
        ("https://[invalid", None),
        ("https://example.com:invalid", None),
        ("https://user@example.com", None),
        ("https://google.com/goto?url=example", None),
    ],
)
def test_normalize_domain(website, expected):
    service = BusinessDeduplicationService()

    assert service.normalize_domain(website) == expected


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("+9779846041887", "+9779846041887"),
        ("+977 9846041887", "+9779846041887"),
        ("abc", ""),
        ("123", ""),
        ("", ""),
    ],
)
def test_normalize_phone_validates_numbers(phone, expected):
    service = BusinessDeduplicationService()

    assert service.normalize_phone(phone) == expected


def test_normalize_local_phone_using_known_region():
    service = BusinessDeduplicationService()

    assert (
        service.normalize_phone(
            "9846041887",
            region="NP",
        )
        == "+9779846041887"
    )


def test_do_not_merge_matching_invalid_phone_numbers():
    service = BusinessDeduplicationService()

    first = Business(
        name="Company A",
        phone_numbers=["123"],
    )

    second = Business(
        name="Company B",
        phone_numbers=["123"],
    )

    assert service.are_duplicates(first, second) is False


def test_merge_equivalent_international_phone_formats():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        phone_numbers=["+977 9846041887"],
    )

    second = Business(
        name="Example Business",
        phone_numbers=["+9779846041887"],
    )

    result = service.deduplicate([first, second])

    assert len(result) == 1

    assert result[0].phone_numbers == ["+9779846041887"]


def test_merge_local_and_international_phone_numbers():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        country_code="NP",
        phone_numbers=["9846041887"],
    )

    second = Business(
        name="Example Business",
        phone_numbers=["+9779846041887"],
    )

    result = service.deduplicate([first, second])

    assert len(result) == 1

    assert result[0].phone_numbers == ["+9779846041887"]


@pytest.mark.parametrize(
    ("field_name", "first_value", "second_value"),
    [
        ("city", "Kathmandu", "Pokhara"),
        ("district", "Kathmandu", "Kaski"),
        ("state", "Bagmati", "Gandaki"),
        ("country", "Nepal", "India"),
        ("country_code", "NP", "IN"),
    ],
)
def test_geographic_conflicts_prevent_domain_merge(
    field_name,
    first_value,
    second_value,
):
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        **{field_name: first_value},
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        **{field_name: second_value},
    )

    assert service.are_duplicates(first, second) is False


def test_geographic_conflict_prevents_phone_merge():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Kathmandu",
        city="Kathmandu",
        phone_numbers=["+9779846041887"],
    )

    second = Business(
        name="Example Pokhara",
        city="Pokhara",
        phone_numbers=["+9779846041887"],
    )

    assert service.are_duplicates(first, second) is False


def test_address_conflict_prevents_domain_merge():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        address="Kathmandu, Nepal",
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        address="Pokhara, Nepal",
    )

    assert service.are_duplicates(first, second) is False


def test_matching_geographic_values_ignore_case():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        city="Kathmandu",
        country="Nepal",
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        city="kathmandu",
        country="NEPAL",
    )

    assert service.are_duplicates(first, second) is True


def test_merge_fills_missing_geographic_fields():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        address="Thamel, Kathmandu, Nepal",
        city="Kathmandu",
        district="Kathmandu",
        state="Bagmati",
        country="Nepal",
        country_code="NP",
        category="Travel agency",
    )

    result = service.merge_business(first, second)

    assert result.address == "Thamel, Kathmandu, Nepal"
    assert result.city == "Kathmandu"
    assert result.district == "Kathmandu"
    assert result.state == "Bagmati"
    assert result.country == "Nepal"
    assert result.country_code == "NP"
    assert result.category == "Travel agency"


def test_merge_preserves_existing_business_name():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business Pvt. Ltd.",
        website="https://example.com",
    )

    second = Business(
        name="Example",
        website="https://example.com",
    )

    result = service.merge_business(first, second)

    assert result.name == "Example Business Pvt. Ltd."


def test_merge_preserves_existing_known_fields():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        city="Kathmandu",
        category="Travel agency",
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        city="kathmandu",
        category="Tour operator",
    )

    result = service.merge_business(first, second)

    assert result.city == "Kathmandu"
    assert result.category == "Travel agency"


def test_merge_replaces_invalid_website():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="invalid-url",
        phone_numbers=["+9779846041887"],
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        phone_numbers=["+9779846041887"],
    )

    result = service.merge_business(first, second)

    assert result.website == "https://example.com"


def test_merge_deduplicates_emails_case_insensitively():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        emails=[
            "INFO@example.com",
            "sales@example.com",
        ],
    )

    result = service.merge_business(first, second)

    assert result.emails == [
        "info@example.com",
        "sales@example.com",
    ]


def test_merge_preserves_unrecognized_phone_values():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        phone_numbers=["123"],
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        phone_numbers=["+9779846041887"],
    )

    result = service.merge_business(first, second)

    assert result.phone_numbers == [
        "123",
        "+9779846041887",
    ]


def test_merge_source_and_contact_page_urls():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        source_urls=[
            "https://example.com",
        ],
        contact_page_urls=[
            "https://example.com/contact",
        ],
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        source_urls=[
            "https://example.com",
            "https://example.com/contact",
        ],
        contact_page_urls=[
            "https://example.com/contact",
            "https://example.com/about",
        ],
    )

    result = service.merge_business(first, second)

    assert result.source_urls == [
        "https://example.com",
        "https://example.com/contact",
    ]

    assert result.contact_page_urls == [
        "https://example.com/contact",
        "https://example.com/about",
    ]


@pytest.mark.parametrize(
    ("existing_status", "incoming_status", "expected"),
    [
        ("pending", "success", "success"),
        ("success", "pending", "success"),
        ("success", "success", "success"),
        ("failed", "failed", "failed"),
        ("success", "failed", "partial"),
        ("failed", "success", "partial"),
        ("success", "no_contacts", "partial"),
        ("partial", "success", "partial"),
        ("no_website", "success", "success"),
        ("success", "no_website", "success"),
        ("no_contacts", "no_contacts", "no_contacts"),
        ("pending", "pending", "pending"),
        ("failed", "no_contacts", "partial"),
    ],
)
def test_merge_extraction_status(
    existing_status,
    incoming_status,
    expected,
):
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        extraction_status=ExtractionStatus(existing_status),
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        extraction_status=ExtractionStatus(incoming_status),
    )

    result = service.merge_business(first, second)

    assert result.extraction_status == ExtractionStatus(expected)


@pytest.mark.parametrize(
    "additional_fields",
    [
        {"emails": ["sales@example.com"]},
        {"phone_numbers": ["+9779846041887"]},
        {"address": "Kathmandu, Nepal"},
        {"category": "Travel agency"},
        {"country_code": "NP"},
    ],
)
def test_merge_invalidates_score_when_scoring_inputs_change(
    additional_fields,
):
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        lead_score=15,
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        **additional_fields,
    )

    result = service.merge_business(first, second)

    assert result.lead_score is None
    assert result.lead_quality is None


def test_merge_invalidates_score_when_website_added():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        phone_numbers=["+9779846041887"],
        lead_score=20,
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        phone_numbers=["+9779846041887"],
    )

    result = service.merge_business(first, second)

    assert result.website == "https://example.com"
    assert result.lead_score is None


def test_merge_preserves_score_when_scoring_inputs_unchanged():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        lead_score=15,
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        source_urls=[
            "https://example.com/contact",
        ],
    )

    result = service.merge_business(first, second)

    assert result.lead_score == 15
    assert result.lead_quality == "Low"


def test_merge_does_not_copy_incoming_score():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        lead_score=15,
    )

    result = service.merge_business(first, second)

    assert result.lead_score is None


def test_merge_rejects_conflicting_businesses():
    service = BusinessDeduplicationService()

    first = Business(
        name="Company A",
        website="https://company-a.com",
    )

    second = Business(
        name="Company B",
        website="https://company-b.com",
    )

    with pytest.raises(ValueError, match="Cannot merge"):
        service.merge_business(first, second)


def test_merge_rejects_insufficient_identity_information():
    service = BusinessDeduplicationService()

    first = Business(name="Company A")
    second = Business(name="Company B")

    with pytest.raises(ValueError, match="Cannot merge"):
        service.merge_business(first, second)


def test_deduplication_preserves_ambiguous_matches():
    service = BusinessDeduplicationService()

    first = Business(
        name="Kathmandu Branch",
        website="https://example.com",
        city="Kathmandu",
    )

    second = Business(
        name="Pokhara Branch",
        website="https://example.com",
        city="Pokhara",
    )

    ambiguous = Business(
        name="Example Business",
        website="https://example.com",
    )

    result = service.deduplicate([first, second, ambiguous])

    assert len(result) == 3

    assert result == [
        first,
        second,
        ambiguous,
    ]


def test_deduplication_preserves_input_order():
    service = BusinessDeduplicationService()

    first = Business(
        name="First Business",
        website="https://first.com",
    )

    second = Business(
        name="Second Business",
        website="https://second.com",
    )

    duplicate = Business(
        name="First Business Duplicate",
        website="https://www.first.com",
    )

    result = service.deduplicate([first, second, duplicate])

    assert result == [first, second]


def test_deduplication_handles_empty_input():
    service = BusinessDeduplicationService()

    assert service.deduplicate([]) == []


def test_merge_does_not_modify_incoming_business():
    service = BusinessDeduplicationService()

    first = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
    )

    second = Business(
        name="Example Business",
        website="https://example.com",
        emails=["sales@example.com"],
    )

    service.merge_business(first, second)

    assert second.emails == ["sales@example.com"]

    assert first.emails == [
        "info@example.com",
        "sales@example.com",
    ]


def test_repeated_deduplication_is_stable():
    service = BusinessDeduplicationService()

    businesses = [
        Business(
            name="Example Business",
            website="https://example.com",
            emails=["info@example.com"],
        ),
        Business(
            name="Example Business Duplicate",
            website="https://www.example.com",
            emails=["sales@example.com"],
        ),
    ]

    first_result = service.deduplicate(businesses)
    second_result = service.deduplicate(first_result)

    assert len(second_result) == 1

    assert second_result[0].emails == [
        "info@example.com",
        "sales@example.com",
    ]
