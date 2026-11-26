from unittest.mock import MagicMock, patch

import pytest

from src.lead_intelligence.extractors.contact_extractor import (
    extract_emails,
    extract_html_contacts,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.scrapers.website_scraper import FetchedPage
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService


class PageMock(MagicMock):
    def __call__(self, *args, **kwargs):
        value = super().__call__(*args, **kwargs)
        return FetchedPage(value, args[0]) if isinstance(value, str) else value


MODULE = "src.lead_intelligence.services.contact_discovery"


@pytest.mark.parametrize("text", ["a@b@example.com", "bad..name@example.com"])
def test_does_not_extract_invalid_email_fragment(text):
    assert extract_emails(text) == []


def test_contact_links_and_visible_text():
    html = """
    <p>info@example.com</p>
    <a href="MAILTO:sales%40example.com?body=hidden@example.com">Email</a>
    <a href="tel:+1-202-555-0123;ext=5">Call</a>
    <script>ignored@example.com</script>
    <template><a href="mailto:ignored@example.com">Ignored</a></template>
    """
    emails, phones = extract_html_contacts(html)
    assert emails == ["info@example.com", "sales@example.com"]
    assert phones == ["+12025550123"]


def test_multiple_recipients_and_duplicates():
    html = '<a href="mailto:INFO@example.com,sales@example.com">info@example.com</a>'
    assert extract_html_contacts(html) == (
        ["info@example.com", "sales@example.com"],
        [],
    )


def test_contact_page_links_and_business_region():
    business = Business(
        name="Agency",
        website="https://example.com",
        country_code="US",
        emails=["INFO@example.com"],
    )
    homepage = '<a href="/contact">Contact</a>'
    page = '<a href="tel:2025550123">Call</a><a href="mailto:info@example.com">Mail</a>'
    with (
        patch(f"{MODULE}.fetch_homepage", new_callable=PageMock, return_value=homepage),
        patch(
            f"{MODULE}.fetch_contact_page",
            new_callable=PageMock,
            return_value=page,
        ) as fetch,
    ):
        result = ContactDiscoveryService().discover(business, region="NP")
    fetch.assert_called_once_with("https://example.com/contact")
    assert result.emails == ["INFO@example.com"]
    assert result.phone_numbers == ["+12025550123"]
    assert result.source_urls == ["https://example.com/contact"]
    assert result.extraction_status == ExtractionStatus.SUCCESS
