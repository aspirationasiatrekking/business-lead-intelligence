from unittest.mock import MagicMock, patch

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.scrapers.website_scraper import (
    FetchedPage,
    find_contact_pages,
)
from src.lead_intelligence.services.contact_discovery import (
    ContactDiscoveryService,
)


class PageMock(MagicMock):
    def __call__(self, *args, **kwargs):
        value = super().__call__(*args, **kwargs)
        return FetchedPage(value, args[0]) if isinstance(value, str) else value


MODULE = "src.lead_intelligence.services.contact_discovery"


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_successful_contact_discovery(
    mock_homepage,
    mock_fetch,
    mock_contact_pages,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
    )

    mock_homepage.return_value = """
        <html>
            <body>
                info@example.com
            </body>
        </html>
    """

    mock_contact_pages.return_value = ["https://example.com/contact"]

    mock_fetch.return_value = "+9779812345678"

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.emails == ["info@example.com"]
    assert result.phone_numbers == ["+9779812345678"]

    mock_homepage.assert_called_once_with("https://example.com")

    mock_fetch.assert_called_once_with("https://example.com/contact")


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_without_website(
    mock_homepage,
    mock_fetch,
):
    business = Business(name="Nepal Trekking")

    service = ContactDiscoveryService()
    result = service.discover(business)

    assert result.emails == []
    assert result.phone_numbers == []

    mock_homepage.assert_not_called()
    mock_fetch.assert_not_called()


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_website_fetch_failure(
    mock_homepage,
    mock_contact_pages,
    mock_fetch,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
    )

    mock_homepage.return_value = None

    service = ContactDiscoveryService()
    result = service.discover(business)

    assert result.emails == []
    assert result.phone_numbers == []

    mock_homepage.assert_called_once_with("https://example.com")

    mock_contact_pages.assert_not_called()
    mock_fetch.assert_not_called()


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_preserve_existing_phone_numbers(
    mock_homepage,
    mock_contact_pages,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
        phone_numbers=["+9779811111111"],
    )

    mock_homepage.return_value = """
        <html>
            <body>
                +9779822222222
            </body>
        </html>
    """

    mock_contact_pages.return_value = []

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.phone_numbers == [
        "+9779811111111",
        "+9779822222222",
    ]


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_remove_duplicate_contacts(
    mock_homepage,
    mock_contact_pages,
):
    business = Business(
        name="Nepal Trekking",
        website="https://example.com",
        emails=["info@example.com"],
        phone_numbers=["+9779812345678"],
    )

    mock_homepage.return_value = """
        <html>
            <body>
                info@example.com
                sales@example.com
                +9779812345678
                +9779822222222
            </body>
        </html>
    """

    mock_contact_pages.return_value = []

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


@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_homepage_failure_preserves_existing_contacts(
    mock_homepage,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
        phone_numbers=["+9779812345678"],
    )

    mock_homepage.return_value = None

    service = ContactDiscoveryService()
    result = service.discover(business, region="NP")

    assert result.emails == ["info@example.com"]
    assert result.phone_numbers == ["+9779812345678"]


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_limits_contact_pages_to_five(
    mock_homepage,
    mock_fetch,
    mock_contact_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<html></html>"

    mock_contact_pages.return_value = [
        f"https://example.com/contact-{index}" for index in range(10)
    ]

    mock_fetch.return_value = "Contact information"

    service = ContactDiscoveryService()
    service.discover(business)

    assert mock_fetch.call_count == 5

    fetched_urls = [call.args[0] for call in mock_fetch.call_args_list]

    assert fetched_urls == [
        f"https://example.com/contact-{index}" for index in range(5)
    ]


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_continues_after_contact_page_failure(
    mock_homepage,
    mock_fetch,
    mock_contact_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = """
        <html>
            <body>info@example.com</body>
        </html>
    """

    mock_contact_pages.return_value = [
        "https://example.com/contact",
        "https://example.com/about",
    ]

    mock_fetch.side_effect = [
        None,
        "sales@example.com",
    ]

    service = ContactDiscoveryService()
    result = service.discover(business)

    assert result.emails == [
        "info@example.com",
        "sales@example.com",
    ]

    assert mock_fetch.call_count == 2


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_returns_same_business_instance(
    mock_homepage,
    mock_contact_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<html></html>"
    mock_contact_pages.return_value = []

    service = ContactDiscoveryService()

    result = service.discover(business)

    assert result is business


# Extraction lifecycle and source provenance tests


@pytest.mark.parametrize(
    "website",
    [
        None,
        "invalid-url",
        "ftp://example.com",
        "https://[invalid",
        "https://google.com/goto?url=example",
    ],
)
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_sets_no_website_status(
    mock_homepage,
    website,
):
    business = Business(
        name="Example Business",
        website=website,
    )

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.NO_WEBSITE

    mock_homepage.assert_not_called()


@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_sets_failed_status(mock_homepage):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = None

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.FAILED


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_sets_success_status(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>info@example.com</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.emails == ["info@example.com"]


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_sets_no_contacts_status(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        phone_numbers=["+9779812345678"],
    )

    mock_homepage.return_value = "<p>No contact information</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.NO_CONTACTS
    assert result.phone_numbers == ["+9779812345678"]


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_sets_partial_status(
    mock_homepage,
    mock_pages,
    mock_fetch,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>info@example.com</p>"

    mock_pages.return_value = [
        "https://example.com/contact",
        "https://example.com/about",
    ]

    mock_fetch.side_effect = [
        None,
        "sales@example.com",
    ]

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.PARTIAL

    assert result.emails == [
        "info@example.com",
        "sales@example.com",
    ]


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_empty_page_text_is_not_fetch_failure(
    mock_homepage,
    mock_pages,
    mock_fetch,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<html></html>"

    mock_pages.return_value = ["https://example.com/contact"]

    mock_fetch.return_value = ""

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.NO_CONTACTS


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_records_contributing_source_urls(
    mock_homepage,
    mock_pages,
    mock_fetch,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>info@example.com</p>"

    mock_pages.return_value = [
        "https://example.com/contact",
        "https://example.com/about",
        "https://example.com/team",
    ]

    mock_fetch.side_effect = [
        "sales@example.com",
        "No contact information",
        None,
    ]

    result = ContactDiscoveryService().discover(business)

    assert result.source_urls == [
        "https://example.com",
        "https://example.com/contact",
    ]

    assert result.contact_page_urls == [
        "https://example.com/contact",
        "https://example.com/about",
        "https://example.com/team",
    ]

    assert result.extraction_status == ExtractionStatus.PARTIAL


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_preserves_previous_sources(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        source_urls=["https://example.com/previous-contact"],
    )

    mock_homepage.return_value = "<p>info@example.com</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(business)

    assert result.source_urls == [
        "https://example.com/previous-contact",
        "https://example.com",
    ]


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_deduplicates_contact_page_urls(
    mock_homepage,
    mock_pages,
    mock_fetch,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<html></html>"

    mock_pages.return_value = [
        "https://example.com/contact",
        "https://example.com/contact",
        "https://example.com/about",
    ]

    mock_fetch.return_value = "info@example.com"

    result = ContactDiscoveryService().discover(business)

    assert result.contact_page_urls == [
        "https://example.com/contact",
        "https://example.com/about",
    ]

    assert mock_fetch.call_count == 2


@patch(f"{MODULE}.fetch_contact_page", new_callable=PageMock)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_tracks_all_pages_but_limits_fetching(
    mock_homepage,
    mock_pages,
    mock_fetch,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<html></html>"

    mock_pages.return_value = [
        f"https://example.com/contact-{index}" for index in range(10)
    ]

    mock_fetch.return_value = "No contact information"

    result = ContactDiscoveryService().discover(business)

    assert len(result.contact_page_urls) == 10
    assert mock_fetch.call_count == 5
    assert result.source_urls == []


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_invalidates_stale_lead_score(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        lead_score=50,
    )

    mock_homepage.return_value = "<p>info@example.com</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(business)

    assert result.emails == ["info@example.com"]
    assert result.lead_score is None
    assert result.lead_quality is None


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_preserves_score_when_contacts_unchanged(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
        lead_score=50,
    )

    mock_homepage.return_value = "<p>info@example.com</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(business)

    assert result.lead_score == 50


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_repeated_discovery_does_not_duplicate_sources(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>info@example.com</p>"
    mock_pages.return_value = []

    service = ContactDiscoveryService()

    service.discover(business)
    service.discover(business)

    assert business.emails == ["info@example.com"]

    assert business.source_urls == ["https://example.com"]


@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_failed_rediscovery_preserves_previous_contacts(
    mock_homepage,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
        source_urls=["https://example.com"],
        contact_page_urls=["https://example.com/contact"],
        extraction_status=ExtractionStatus.SUCCESS,
        lead_score=60,
    )

    mock_homepage.return_value = None

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.FAILED

    assert result.emails == ["info@example.com"]
    assert result.source_urls == ["https://example.com"]
    assert result.contact_page_urls == []
    assert result.lead_score == 60


@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_handles_contact_page_parsing_failure(
    mock_homepage,
    mock_pages,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>info@example.com</p>"

    mock_pages.side_effect = ValueError("Invalid contact page URL")

    result = ContactDiscoveryService().discover(business)

    assert result.extraction_status == ExtractionStatus.PARTIAL
    assert result.emails == ["info@example.com"]
    assert result.source_urls == ["https://example.com"]


@pytest.mark.parametrize(
    "region",
    ["NP", "np", " Np "],
)
@patch(f"{MODULE}.find_contact_pages")
@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_discovery_normalizes_phone_region(
    mock_homepage,
    mock_pages,
    region,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    mock_homepage.return_value = "<p>9846041887</p>"
    mock_pages.return_value = []

    result = ContactDiscoveryService().discover(
        business,
        region=region,
    )

    assert result.phone_numbers == ["+9779846041887"]


@patch(f"{MODULE}.fetch_homepage", new_callable=PageMock)
def test_invalid_region_rejected_before_network_request(
    mock_homepage,
):
    business = Business(
        name="Example Business",
        website="https://example.com",
    )

    with pytest.raises(ValueError):
        ContactDiscoveryService().discover(
            business,
            region="NPL",
        )

    mock_homepage.assert_not_called()


def test_contact_page_discovery_skips_malformed_links():
    html = """
        <html>
            <body>
                <a href="https://[invalid">Contact</a>
                <a href="https://example.com:invalid/about">
                    About
                </a>
                <a href="https://user@example.com/contact">
                    Contact
                </a>
                <a href="https://other.com/contact">
                    External contact
                </a>
                <a href="mailto:info@example.com">
                    Contact
                </a>
                <a href="/contact">
                    Contact us
                </a>
            </body>
        </html>
    """

    pages = find_contact_pages(
        "https://example.com",
        html,
    )

    assert pages == ["https://example.com/contact"]


def test_contact_page_discovery_removes_fragments():
    html = """
        <html>
            <body>
                <a href="/contact#phone">Contact</a>
                <a href="/contact#email">Contact</a>
            </body>
        </html>
    """

    pages = find_contact_pages(
        "https://example.com",
        html,
    )

    assert pages == ["https://example.com/contact"]
