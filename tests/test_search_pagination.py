from unittest.mock import Mock

import pytest
import requests

from src.lead_intelligence.models.search_request import (
    SearchRequest,
)
from src.lead_intelligence.search.serper_provider import (
    SerperResponseError,
)
from src.lead_intelligence.services.business_search import (
    BusinessSearchService,
)


def make_page(
    start: int,
    count: int = 10,
    credits: int = 1,
):
    return {
        "places": [
            {
                "title": f"Business {index}",
                "website": (f"https://business{index}.com"),
                "cid": str(index),
            }
            for index in range(
                start,
                start + count,
            )
        ],
        "credits": credits,
    }


def make_service(responses):
    provider = Mock()

    provider.search_places.side_effect = responses

    service = BusinessSearchService(provider=provider)

    return service, provider


def test_search_retrieves_multiple_pages():
    service, provider = make_service(
        [
            make_page(1),
            make_page(11),
            make_page(21),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        country="np",
        max_results=30,
    )

    assert result.total_returned == 30

    assert result.pages_requested == 3
    assert result.pages_processed == 3

    assert result.reported_credits == 3

    assert result.stop_reason == ("result_limit_reached")

    assert [call.kwargs["page"] for call in provider.search_places.call_args_list] == [
        1,
        2,
        3,
    ]

    assert all(
        call.kwargs["num"] == 10 for call in provider.search_places.call_args_list
    )


def test_search_stops_after_requested_result_count():
    service, provider = make_service(
        [
            make_page(1),
            make_page(11),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=15,
    )

    assert result.total_returned == 15

    assert result.total_discovered == 20

    assert provider.search_places.call_count == 2


def test_search_returns_five_from_one_page():
    service, provider = make_service([make_page(1)])

    result = service.search_with_report(
        "Travel agencies",
        max_results=5,
    )

    assert result.total_returned == 5

    assert result.total_discovered == 10

    assert result.reported_credits == 1

    assert provider.search_places.call_count == 1


def test_search_supports_one_hundred_results():
    service, provider = make_service([make_page(page * 10 + 1) for page in range(10)])

    result = service.search_with_report(
        "Travel agencies",
        max_results=100,
    )

    assert result.total_returned == 100

    assert result.pages_requested == 10

    assert result.reported_credits == 10

    assert provider.search_places.call_count == 10


def test_search_stops_on_empty_page():
    service, provider = make_service(
        [
            make_page(1),
            make_page(11, count=0),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.total_returned == 10

    assert result.stop_reason == "empty_page"

    assert result.reported_credits == 2

    assert provider.search_places.call_count == 2


def test_search_handles_empty_first_page():
    service, provider = make_service([make_page(1, count=0)])

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.businesses == []

    assert result.pages_processed == 1

    assert result.stop_reason == "empty_page"

    assert provider.search_places.call_count == 1


def test_search_continues_after_short_page():
    service, provider = make_service(
        [
            make_page(1, count=3),
            make_page(4, count=7),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=10,
    )

    assert result.total_returned == 10

    assert provider.search_places.call_count == 2


def test_search_stops_on_repeated_page():
    page = make_page(1)

    service, provider = make_service([page, page])

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.total_returned == 10

    assert result.stop_reason == "repeated_page"

    assert result.is_partial is True

    assert result.reported_credits == 2

    assert provider.search_places.call_count == 2


def test_repeated_page_detection_ignores_order():
    first = make_page(1)

    second = {
        "places": list(reversed(first["places"])),
        "credits": 1,
    }

    service, provider = make_service([first, second])

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.stop_reason == "repeated_page"

    assert provider.search_places.call_count == 2


def test_deduplicates_across_multiple_pages():
    service, _ = make_service(
        [
            make_page(1),
            make_page(6),
            make_page(16),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=20,
    )

    assert result.total_returned == 20

    assert result.total_discovered == 30

    assert result.duplicate_count == 5

    assert result.pages_requested == 3


def test_mapping_failures_preserve_global_indexes():
    service, _ = make_service(
        [
            {
                "places": [
                    {"title": "Business One"},
                    None,
                ],
                "credits": 1,
            },
            {
                "places": [
                    {"title": "Business Two"},
                    None,
                ],
                "credits": 1,
            },
            {
                "places": [],
                "credits": 1,
            },
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=10,
    )

    assert result.total_discovered == 4

    assert result.total_mapped == 2

    assert result.total_failed == 2

    assert [failure.item_index for failure in result.failures] == [1, 3]


def test_search_respects_page_budget(monkeypatch):
    service, provider = make_service(
        [
            make_page(1),
            make_page(11),
        ]
    )

    monkeypatch.setattr(
        service,
        "MAX_SEARCH_PAGES",
        2,
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=100,
    )

    assert result.total_returned == 20

    assert result.stop_reason == ("page_budget_reached")

    assert result.is_partial is True

    assert provider.search_places.call_count == 2


def test_stops_after_consecutive_pages_without_progress():
    first = make_page(1)

    second = make_page(1)

    third = make_page(1)

    # Missing CIDs allow domain matching.
    # Different valid CIDs prevent merging.
    for index, place in enumerate(second["places"]):
        place.pop("cid")
        place["title"] += f" alias {index}"

    for index, place in enumerate(third["places"]):
        place.pop("cid")
        place["title"] += f" alternate {index}"

    service, provider = make_service([first, second, third])

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.total_returned == 10

    assert result.duplicate_count == 20

    assert result.stop_reason == "no_progress"

    assert provider.search_places.call_count == 3


def test_preserves_results_after_later_provider_failure():
    service, provider = make_service(
        [
            make_page(1),
            requests.exceptions.Timeout("Provider timed out"),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=50,
    )

    assert result.total_returned == 10

    assert result.pages_requested == 2

    assert result.pages_processed == 1

    assert result.stop_reason == "provider_error"

    assert result.is_partial is True

    assert result.warnings

    assert provider.search_places.call_count == 2


def test_first_page_provider_failure_is_raised():
    service, provider = make_service(
        [requests.exceptions.ConnectionError("Provider unavailable")]
    )

    with pytest.raises(requests.exceptions.ConnectionError):
        service.search_with_report(
            "Travel agencies",
            max_results=50,
        )

    assert provider.search_places.call_count == 1


def test_invalid_provider_response_is_rejected():
    service, _ = make_service([{"unexpected": []}])

    with pytest.raises(SerperResponseError):
        service.search_with_report("Travel agencies")


@pytest.mark.parametrize(
    "credits",
    [
        None,
        "1",
        -1,
        True,
        1.5,
    ],
)
def test_tracks_unknown_credit_information(
    credits,
):
    page = make_page(1)

    page["credits"] = credits

    service, _ = make_service([page])

    result = service.search_with_report("Travel agencies")

    assert result.reported_credits == 0

    assert result.unknown_credit_responses == 1

    assert result.credit_tracking_complete is False


def test_tracks_zero_reported_credits():
    service, _ = make_service([make_page(1, credits=0)])

    result = service.search_with_report("Travel agencies")

    assert result.reported_credits == 0

    assert result.credit_tracking_complete is True


def test_adds_credits_from_all_pages():
    service, _ = make_service(
        [
            make_page(1, credits=2),
            make_page(11, credits=3),
        ]
    )

    result = service.search_with_report(
        "Travel agencies",
        max_results=20,
    )

    assert result.reported_credits == 5


def test_resolve_credits_are_recorded():
    original = make_page(1)

    original["places"][0]["website"] = "https://google.com/goto?url=example"

    service, provider = make_service([original])

    provider.resolve_links.return_value = make_page(1, credits=2)

    result = service.search_with_report("Travel agencies")

    assert result.resolve_requests == 1

    assert result.reported_credits == 3

    assert result.total_returned == 10


def test_resolve_failure_preserves_original_results():
    page = make_page(1)

    page["places"][0]["website"] = "https://google.com/goto?url=example"

    service, provider = make_service([page])

    provider.resolve_links.side_effect = requests.exceptions.Timeout("Resolve failed")

    result = service.search_with_report("Travel agencies")

    assert result.total_returned == 10

    assert result.resolve_requests == 1

    assert result.businesses[0].website is None

    assert result.warnings

    assert result.is_partial is True


def test_resolve_is_skipped_without_google_redirects():
    service, provider = make_service([make_page(1)])

    result = service.search_with_report("Travel agencies")

    assert result.resolve_requests == 0

    provider.resolve_links.assert_not_called()


def test_structured_request_survives_pagination():
    service, _ = make_service(
        [
            make_page(1),
            make_page(11),
        ]
    )

    search_request = SearchRequest(
        country_code="GB",
        city="London",
        query="Travel agencies",
        max_results=20,
    )

    result = service.search_request(search_request)

    assert result.request == search_request

    assert result.total_returned == 20

    assert result.pages_requested == 2


@pytest.mark.parametrize(
    "query",
    [
        "",
        " ",
        None,
        123,
        True,
    ],
)
def test_invalid_query_never_reaches_provider(query):
    service, provider = make_service([])

    with pytest.raises((ValueError, TypeError)):
        service.search_with_report(query)

    provider.search_places.assert_not_called()
