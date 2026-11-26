from unittest.mock import Mock

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.scrapers.website_scraper import FetchedPage
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.website_acquisition import WebsiteAcquisitionService
from src.lead_intelligence.settings import ApplicationSettings

MODULE = "src.lead_intelligence.services.website_acquisition"


def test_verified_candidate(monkeypatch):
    business = Business("Alpine Agency", phone_numbers=["+12025550123"])
    page = FetchedPage(
        "<title>Alpine Agency</title><a href='tel:+12025550123'>Call</a>",
        "https://alpine.example.com",
    )
    monkeypatch.setattr(f"{MODULE}.fetch_website_page", Mock(return_value=page))
    assert WebsiteAcquisitionService().acquire(
        business, {"organic": [{"link": page.final_url}]}, "US"
    )
    assert business.website == page.final_url
    assert business.website_source == "organic_name_phone"


def test_name_without_phone_match_is_rejected(monkeypatch):
    business = Business("Alpine Agency", phone_numbers=["+12025550123"])
    page = FetchedPage("<title>Alpine Agency</title>", "https://alpine.example.com")
    monkeypatch.setattr(f"{MODULE}.fetch_website_page", Mock(return_value=page))
    assert not WebsiteAcquisitionService().acquire(
        business, {"organic": [{"link": page.final_url}]}, "US"
    )
    assert business.website is None


def test_fallback_budget():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [
            {"title": "Alpine Agency", "phoneNumber": "+12025550123"},
            {"title": "Other Agency", "phoneNumber": "+12025550124"},
        ],
        "credits": 1,
    }
    provider.search_organic.return_value = {"organic": [], "credits": 1}
    service = BusinessSearchService(
        provider, settings=ApplicationSettings(max_website_searches=1)
    )
    result = service.search_with_report("agencies", country="us", max_results=2)
    assert result.website_search_requests == 1
    assert result.reported_credits == 2
    provider.search_organic.assert_called_once()


def test_default_has_no_paid_fallback():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [{"title": "Alpine Agency", "phoneNumber": "+12025550123"}]
    }
    BusinessSearchService(provider).search_with_report("agencies", max_results=1)
    provider.search_organic.assert_not_called()


def test_candidate_diagnostics_reset_and_distinguish_failures(monkeypatch):
    business = Business("Alpine Agency", phone_numbers=["+12025550123"])
    fetch = Mock(
        side_effect=[
            None,
            FetchedPage("<title>Other Agency</title>", "https://other.example.com"),
            FetchedPage("<title>Alpine Agency</title>", "https://alpine.example.com"),
        ]
    )
    monkeypatch.setattr(f"{MODULE}.fetch_website_page", fetch)
    service = WebsiteAcquisitionService()
    response = {
        "organic": [
            {"link": "https://facebook.com/alpine"},
            {"link": "https://missing.example.com"},
            {"link": "https://other.example.com"},
            {"link": "https://alpine.example.com"},
            {"link": "https://alpine.example.com/about"},
        ]
    }
    assert not service.acquire(business, response, "US")
    assert service.candidate_outcomes == {
        "rejected_url": 1,
        "fetch_or_site_failure": 1,
        "name_mismatch": 1,
        "phone_mismatch": 1,
        "duplicate_or_invalid": 1,
    }
    assert not service.acquire(business, {"organic": []}, "US")
    assert not service.candidate_outcomes


def test_diagnostics_account_for_every_returned_business():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [
            {"title": "Direct Agency", "website": "https://direct.example.com"},
            {"title": "Alpine Agency", "phoneNumber": "+12025550123"},
            {"title": "Other Agency", "phoneNumber": "+12025550124"},
            {"title": "Missing Phone"},
            {"title": "Single", "phoneNumber": "+12025550125"},
        ],
        "credits": 1,
    }
    provider.search_organic.return_value = {"organic": [], "credits": 1}
    service = BusinessSearchService(
        provider, settings=ApplicationSettings(max_website_searches=1)
    )
    result = service.search_with_report("agencies", country="us", max_results=5)
    assert result.website_fallback_outcomes == {
        "already_available": 1,
        "no_match": 1,
        "budget_exhausted": 1,
        "no_phone": 1,
        "insufficient_name": 1,
    }
    assert result.website_source_counts == {
        "places": 1,
        "resolve": 0,
        "organic_name_phone": 0,
        "other": 0,
        "no_website": 4,
    }
    assert result.website_search_requests == 1
    assert result.reported_credits == 2
