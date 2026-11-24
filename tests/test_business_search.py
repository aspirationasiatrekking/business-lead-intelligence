
from unittest.mock import MagicMock

from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.models.business import Business


def test_search_without_redirects():
    service = BusinessSearchService()
    service.provider = MagicMock()

    service.provider.search_places.return_value = {
        "places": [
            {"title": "Business One"},
            {"title": "Business Two"},
        ]
    }

    businesses = service.search("Trekking companies in Nepal")

    assert len(businesses) == 2
    assert all(isinstance(b, Business) for b in businesses)

    service.provider.resolve_links.assert_not_called()


def test_search_with_redirects():
    service = BusinessSearchService()
    service.provider = MagicMock()

    raw_results = {
        "places": [
            {
                "title": "Business One",
                "website": "https://www.google.com/goto?url=example"
            }
        ]
    }

    resolved_results = {
        "places": [
            {
                "title": "Business One",
                "website": "https://example.com"
            }
        ]
    }

    service.provider.search_places.return_value = raw_results
    service.provider.resolve_links.return_value = resolved_results

    businesses = service.search("Trekking companies in Nepal")

    assert len(businesses) == 1
    assert businesses[0].website == "https://example.com"

    service.provider.resolve_links.assert_called_once_with(raw_results)


def test_search_with_no_places():
    service = BusinessSearchService()
    service.provider = MagicMock()

    service.provider.search_places.return_value = {
        "places": []
    }

    businesses = service.search("Unknown businesses")

    assert businesses == []
    service.provider.resolve_links.assert_not_called()
