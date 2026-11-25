from src.lead_intelligence.models.business import Business
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
