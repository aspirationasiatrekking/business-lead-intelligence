from unittest.mock import MagicMock, Mock

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import SearchResult
from src.lead_intelligence.search.serper_provider import SerperSearchProvider
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
    service = BusinessSearchService(provider=MagicMock())

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
    service = BusinessSearchService(provider=MagicMock())

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


# Search reporting tests


def test_search_with_report_success():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {"title": "First Business"},
            {"title": "Second Business"},
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    assert isinstance(result, SearchResult)
    assert result.total_discovered == 2
    assert result.total_mapped == 2
    assert result.total_returned == 2
    assert result.total_failed == 0
    assert result.duplicate_count == 0
    assert result.has_failures is False

    assert result.businesses[0].name == "First Business"
    assert result.businesses[1].name == "Second Business"

    provider.resolve_links.assert_not_called()


def test_search_with_report_empty_results():
    provider = MagicMock()
    provider.search_places.return_value = {"places": []}

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    assert result.businesses == []
    assert result.failures == []
    assert result.total_discovered == 0
    assert result.total_mapped == 0
    assert result.total_returned == 0
    assert result.total_failed == 0
    assert result.duplicate_count == 0
    assert result.has_failures is False


def test_search_with_report_handles_invalid_records():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {"title": "First Business"},
            None,
            "Invalid record",
            {"title": "Second Business"},
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    assert result.total_discovered == 4
    assert result.total_mapped == 2
    assert result.total_returned == 2
    assert result.total_failed == 2
    assert result.duplicate_count == 0
    assert result.has_failures is True

    assert result.failures[0].item_index == 1
    assert result.failures[1].item_index == 2

    assert result.businesses[0].name == "First Business"
    assert result.businesses[1].name == "Second Business"


def test_search_with_report_handles_model_validation_failure():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {"title": "First Business"},
            {
                "title": "Broken Business",
                "address": 123,
            },
            {"title": "Second Business"},
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    assert result.total_discovered == 3
    assert result.total_mapped == 2
    assert result.total_returned == 2
    assert result.total_failed == 1
    assert result.has_failures is True

    failure = result.failures[0]

    assert failure.item_index == 1
    assert failure.item_name == "Broken Business"
    assert failure.stage == "mapping"
    assert "TypeError" in failure.message


def test_search_with_report_counts_duplicates():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://example.com",
            },
            {
                "title": "Example Business",
                "website": "https://example.com",
            },
            {
                "title": "Another Business",
                "website": "https://another.com",
            },
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    assert result.total_discovered == 3
    assert result.total_mapped == 3
    assert result.duplicate_count == 1
    assert result.total_returned == 2
    assert result.total_failed == 0


def test_search_with_report_respects_result_limit():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {"title": "First Business"},
            {"title": "Second Business"},
            {"title": "Third Business"},
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report(
        "Travel agencies",
        max_results=2,
    )

    assert result.total_discovered == 3
    assert result.total_mapped == 3
    assert result.total_returned == 2
    assert result.total_failed == 0
    assert result.duplicate_count == 0


def test_search_with_report_resolves_google_redirects():
    provider = MagicMock()

    raw_results = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://www.google.com/goto?url=example",
            }
        ]
    }

    resolved_results = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://example.com",
            }
        ]
    }

    provider.search_places.return_value = raw_results
    provider.resolve_links.return_value = resolved_results

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report("Travel agencies")

    provider.resolve_links.assert_called_once_with(raw_results)

    assert result.total_returned == 1
    assert result.businesses[0].website == "https://example.com"
    assert result.total_failed == 0


def test_search_with_report_propagates_selected_region():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {
                "title": "Example Business",
                "phoneNumber": "2025550123",
            }
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report(
        query="Travel agencies",
        country="us",
        max_results=10,
    )

    provider.search_places.assert_called_once_with(
        query="Travel agencies",
        country="us",
        page=1,
        num=10,
    )

    assert result.businesses[0].phone_numbers == ["+12025550123"]

    # Search region does not establish business location.
    assert result.businesses[0].country_code is None


def test_search_with_report_propagates_provider_failure():
    provider = MagicMock()
    provider.search_places.side_effect = RuntimeError("Provider unavailable")

    service = BusinessSearchService(provider=provider)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        service.search_with_report("Travel agencies")

    provider.resolve_links.assert_not_called()


def test_search_remains_backward_compatible():
    provider = MagicMock()
    provider.search_places.return_value = {
        "places": [
            {"title": "First Business"},
            None,
            {"title": "Second Business"},
        ]
    }

    service = BusinessSearchService(provider=provider)

    businesses = service.search("Travel agencies")

    assert isinstance(businesses, list)
    assert len(businesses) == 2
    assert businesses[0].name == "First Business"
    assert businesses[1].name == "Second Business"


def test_search_preserves_failures_in_mixed_redirect_batch(
    monkeypatch,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    raw_results = {
        "places": [
            {"title": "First Business"},
            None,
            {
                "title": "Second Business",
                "website": "https://google.com/goto?url=example",
            },
            "Invalid record",
        ]
    }

    mock_post = Mock(return_value=raw_results)

    monkeypatch.setattr(provider, "_post", mock_post)

    with BusinessSearchService(provider=provider) as service:
        result = service.search_with_report(
            query="Travel agencies",
            country="np",
        )

    assert result.total_discovered == 4
    assert result.total_mapped == 2
    assert result.total_returned == 2
    assert result.total_failed == 2
    assert result.duplicate_count == 0

    assert result.businesses[0].name == "First Business"
    assert result.businesses[1].name == "Second Business"

    assert result.businesses[1].website is None

    assert result.failures[0].item_index == 1
    assert result.failures[1].item_index == 3

    mock_post.assert_called_once_with(
        "places",
        {
            "q": "Travel agencies",
            "hl": "en",
            "page": 1,
            "num": 10,
            "gl": "np",
        },
    )


@pytest.mark.parametrize(
    "country",
    ["NP", "np", " Np ", "\tnp\n"],
)
def test_search_normalizes_country_and_phone_region(country):
    provider = MagicMock()

    provider.search_places.return_value = {
        "places": [
            {
                "title": "Nepal Business",
                "phoneNumber": "9846041887",
            }
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report(
        query="Trekking companies",
        country=country,
    )

    provider.search_places.assert_called_once_with(
        query="Trekking companies",
        country="np",
        page=1,
        num=10,
    )

    assert result.total_returned == 1
    assert result.businesses[0].phone_numbers == ["+9779846041887"]

    assert result.businesses[0].country_code is None


@pytest.mark.parametrize(
    "country",
    ["", "NPL", "123", "N1", "日本"],
)
def test_search_rejects_invalid_country_before_provider(
    country,
):
    provider = MagicMock()

    service = BusinessSearchService(provider=provider)

    with pytest.raises(
        ValueError,
        match="Country code must contain two ASCII letters",
    ):
        service.search_with_report(
            query="Travel agencies",
            country=country,
        )

    provider.search_places.assert_not_called()
    provider.resolve_links.assert_not_called()


@pytest.mark.parametrize(
    "country",
    [123, True, [], {}],
)
def test_search_rejects_invalid_country_type_before_provider(
    country,
):
    provider = MagicMock()

    service = BusinessSearchService(provider=provider)

    with pytest.raises(
        TypeError,
        match="Country code must be a string",
    ):
        service.search_with_report(
            query="Travel agencies",
            country=country,
        )

    provider.search_places.assert_not_called()


def test_search_without_country_preserves_none():
    provider = MagicMock()

    provider.search_places.return_value = {
        "places": [
            {
                "title": "Example Business",
                "phoneNumber": "+12025550123",
            }
        ]
    }

    service = BusinessSearchService(provider=provider)

    result = service.search_with_report(
        query="Travel agencies",
    )

    provider.search_places.assert_called_once_with(
        query="Travel agencies",
        country=None,
        page=1,
        num=10,
    )

    assert result.total_returned == 1
    assert result.businesses[0].phone_numbers == ["+12025550123"]
    assert result.businesses[0].country_code is None
