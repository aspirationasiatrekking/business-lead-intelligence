from unittest.mock import patch

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.mapper import map_serper_place
from src.lead_intelligence.scrapers.website_scraper import (
    FetchedPage,
    find_contact_pages,
)
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.utils.website_policy import is_candidate_business_website

MODULE = "src.lead_intelligence.services.contact_discovery"


@pytest.mark.parametrize("host", ["facebook.com", "www.tripadvisor.com", "x.com"])
def test_third_party_website(host):
    url = "https://" + host + "/agency"
    assert not is_candidate_business_website(url)
    assert map_serper_place({"title": "Agency", "website": url}).website is None
    with patch(f"{MODULE}.fetch_homepage") as fetch:
        result = ContactDiscoveryService().discover(Business("Agency", website=url))
    fetch.assert_not_called()
    assert result.extraction_status == ExtractionStatus.NO_WEBSITE


def test_domain_suffix_not_substring():
    assert is_candidate_business_website("https://notfacebook.com")


def test_ranked_multilingual_links_and_queries():
    html = """<a href="/team">Team</a><a href="/about">About</a>
    <a href="/contact?lang=es">Contacto</a>
    <a href="/contact?lang=fr">Contact</a>
    <a href="/local">सम्पर्क</a><a href="/teamwork">Teamwork</a>"""
    assert find_contact_pages("https://example.com", html) == [
        "https://example.com/contact?lang=es",
        "https://example.com/contact?lang=fr",
        "https://example.com/local",
        "https://example.com/about",
        "https://example.com/team",
    ]


def test_final_url_and_contact_provenance():
    home = FetchedPage('<a href="contact">Contact</a>', "https://www.example.com/en/")
    page = FetchedPage(
        "info@example.com +12025550123", "https://www.example.com/en/reach"
    )
    business = Business("Agency", website="https://example.com")
    with (
        patch(f"{MODULE}.fetch_homepage", return_value=home),
        patch(f"{MODULE}.fetch_contact_page", return_value=page) as fetch,
    ):
        ContactDiscoveryService().discover(business)
    fetch.assert_called_once_with("https://www.example.com/en/contact")
    assert business.email_sources == {"info@example.com": [page.final_url]}
    assert business.phone_sources == {"+12025550123": [page.final_url]}
    assert business.source_urls == [page.final_url]


def test_merge_provenance_without_aliasing():
    first = Business(
        "Agency",
        serper_cid="123",
        emails=["info@example.com"],
        email_sources={"info@example.com": ["https://example.com/a"]},
    )
    second = Business(
        "Agency",
        serper_cid="123",
        emails=["info@example.com"],
        email_sources={"info@example.com": ["https://example.com/b"]},
    )
    result = BusinessDeduplicationService().merge_business(first, second)
    assert result.email_sources["info@example.com"] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert second.email_sources["info@example.com"] == ["https://example.com/b"]


def test_cross_site_final_url_is_rejected():
    business = Business("Agency", website="https://example.com")
    page = FetchedPage("info@example.com", "https://other.com")
    with patch(f"{MODULE}.fetch_homepage", return_value=page):
        ContactDiscoveryService().discover(business)
    assert business.emails == []
    assert business.extraction_status == ExtractionStatus.FAILED
