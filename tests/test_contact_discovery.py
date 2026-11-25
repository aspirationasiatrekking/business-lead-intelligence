from unittest.mock import patch

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.contact_discovery import (
    ContactDiscoveryService,
)


@patch("src.lead_intelligence.services.contact_discovery.extract_phone_numbers")
@patch("src.lead_intelligence.services.contact_discovery.extract_emails")
@patch("src.lead_intelligence.services.contact_discovery.fetch_website")
def test_successful_contact_discovery(
    mock_fetch,
    mock_emails,
    mock_phones,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
    )

    mock_fetch.return_value = "Website content"
    mock_emails.return_value = ["info@example.com"]
    mock_phones.return_value = ["+9779812345678"]

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.emails == ["info@example.com"]
    assert result.phone_numbers == ["+9779812345678"]


def test_discovery_without_website():
    business = Business(name="Nepal Trekking")

    service = ContactDiscoveryService()
    result = service.discover(business)

    assert result.emails == []
    assert result.phone_numbers == []


@patch("src.lead_intelligence.services.contact_discovery.fetch_website")
def test_website_fetch_failure(mock_fetch):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
    )

    mock_fetch.return_value = None

    service = ContactDiscoveryService()
    result = service.discover(business)

    assert result.emails == []
    assert result.phone_numbers == []


@patch("src.lead_intelligence.services.contact_discovery.extract_phone_numbers")
@patch("src.lead_intelligence.services.contact_discovery.extract_emails")
@patch("src.lead_intelligence.services.contact_discovery.fetch_website")
def test_preserve_existing_phone_numbers(
    mock_fetch,
    mock_emails,
    mock_phones,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
        phone_numbers=["+9779811111111"],
    )

    mock_fetch.return_value = "Website content"
    mock_emails.return_value = []
    mock_phones.return_value = ["+9779822222222"]

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.phone_numbers == [
        "+9779811111111",
        "+9779822222222",
    ]


@patch("src.lead_intelligence.services.contact_discovery.extract_phone_numbers")
@patch("src.lead_intelligence.services.contact_discovery.extract_emails")
@patch("src.lead_intelligence.services.contact_discovery.fetch_website")
def test_remove_duplicate_contacts(
    mock_fetch,
    mock_emails,
    mock_phones,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
        emails=["info@example.com"],
        phone_numbers=["+9779812345678"],
    )

    mock_fetch.return_value = "Website content"
    mock_emails.return_value = [
        "info@example.com",
        "sales@example.com",
    ]
    mock_phones.return_value = [
        "+9779812345678",
        "+9779822222222",
    ]

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.emails == [
        "info@example.com",
        "sales@example.com",
    ]

    assert result.phone_numbers == [
        "+9779812345678",
        "+9779822222222",
    ]
