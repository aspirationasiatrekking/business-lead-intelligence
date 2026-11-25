from unittest.mock import MagicMock, Mock

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.business_search import BusinessSearchService


def test_search_without_redirects():
    service = BusinessSearchService(provider=MagicMock()) 

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
                "website": "https://www.google.com/goto?url=example",
            }
        ]
    }

    resolved_results = {
        "places": [{"title": "Business One", "website": "https://example.com"}]
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

    service.provider.search_places.return_value = {"places": []}

    businesses = service.search("Unknown businesses")

    assert businesses == []
    service.provider.resolve_links.assert_not_called()


def create_mock_service():
    return BusinessSearchService(provider=MagicMock())


def generate_places(count):
    return [{"title": f"Business {i}"} for i in range(count)]


def test_search_default_max_results():
    service = create_mock_service()

    service.provider.search_places.return_value = {"places": generate_places(20)}

    businesses = service.search("Adventure agencies")

    assert len(businesses) == 10

    service.provider.search_places.assert_called_once_with(
        query="Adventure agencies", country=None, num=10, page=1
    )


def test_search_custom_max_results():
    service = create_mock_service()

    service.provider.search_places.return_value = {"places": generate_places(20)}

    businesses = service.search(
        "Adventure agencies",
        max_results=5,
    )

    assert len(businesses) == 5

    service.provider.search_places.assert_called_once_with(
        query="Adventure agencies", country=None, num=5, page=1
    )


def test_search_maximum_allowed_results():
    service = create_mock_service()

    service.provider.search_places.return_value = {"places": generate_places(110)}

    businesses = service.search(
        "Adventure agencies",
        max_results=100,
    )

    assert len(businesses) == 100

    service.provider.search_places.assert_called_once_with(
        query="Adventure agencies", country=None, num=100, page=1
    )


@pytest.mark.parametrize(
    "max_results",
    [0, -1, 101, 1.5, "10", True],
)
def test_search_rejects_invalid_max_results(max_results):
    service = create_mock_service()

    with pytest.raises((ValueError, TypeError)):
        service.search(
            "Adventure agencies",
            max_results=max_results,
        )

    service.provider.search_places.assert_not_called()


def test_context_manager_closes_provider(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    with BusinessSearchService() as service:
        provider = service.provider
        provider.close = Mock()

    provider.close.assert_called_once()


def generate_paginated_places(page, count=10):
    return {
        "places": [
            {
                "title": f"Business {page}_{i}",
                "website": f"https://business{page}_{i}.com",
            }
            for i in range(count)
        ]
    }


def test_search_uses_single_page_when_default_results_are_enough():
    service = create_mock_service()

    service.provider.search_places.return_value = generate_paginated_places(
        page=1,
        count=10,
    )

    businesses = service.search("Adventure agencies")

    assert len(businesses) == 10

    service.provider.search_places.assert_called_once_with(
        query="Adventure agencies",
        country=None,
        page=1,
        num=10,
    )


def test_search_deduplicates_businesses():
    service = create_mock_service()

    service.provider.search_places.return_value = {
        "places": [
            {
                "title": "Nepal Hiking Team",
                "website": "https://www.nepalhikingteam.com/",
                "phoneNumber": "+9779846041887",
            },
            {
                "title": "Nepal Hiking Team Pvt Ltd",
                "website": "https://nepalhikingteam.com/about",
                "phoneNumber": "+9779846041887",
            },
        ]
    }

    businesses = service.search("Trekking companies")

    assert len(businesses) == 1
    assert businesses[0].name == "Nepal Hiking Team"
