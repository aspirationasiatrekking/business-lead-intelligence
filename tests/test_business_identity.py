from unittest.mock import Mock

import pytest
import requests

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import map_serper_place
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.utils.business_identity import normalize_serper_cid


@pytest.mark.parametrize(
    "value",
    [None, True, 123, "0", "-1", "1.2", "abc", "", "18446744073709551616", "１２３"],
)
def test_invalid_cid(value):
    assert normalize_serper_cid(value) is None
    assert map_serper_place({"title": "Agency", "cid": value}).serper_cid is None


@pytest.mark.parametrize(
    "value, expected",
    [(" 00123 ", "123"), ("18446744073709551615", "18446744073709551615")],
)
def test_valid_cid(value, expected):
    assert Business(name="Agency", serper_cid=value).serper_cid == expected
    assert map_serper_place({"title": "Agency", "cid": value}).serper_cid == expected


def test_invalid_model_cid():
    with pytest.raises(ValueError, match="CID"):
        Business(name="Agency", serper_cid="bad")


@pytest.mark.parametrize(
    "field, value",
    [
        ("latitude", 91),
        ("longitude", -181),
        ("latitude", float("nan")),
        ("longitude", float("inf")),
        ("latitude", True),
        ("longitude", "12"),
    ],
)
def test_invalid_coordinates(field, value):
    with pytest.raises(ValueError, match=field):
        Business(name="Agency", **{field: value})
    business = map_serper_place({"title": "Agency", field: value})
    assert getattr(business, field) is None


def test_mapper_preserves_coordinates_without_inventing_geography():
    business = map_serper_place(
        {"title": "Agency", "latitude": 27.7, "longitude": 85.3}, region="NP"
    )
    assert (business.latitude, business.longitude) == (27.7, 85.3)
    assert business.country_code is None
    assert business.city is None


def test_same_cid_matches_without_contact_data():
    service = BusinessDeduplicationService()
    first = Business(name="Agency", serper_cid="123")
    second = Business(
        name="Agency Ltd",
        serper_cid="123",
        emails=["info@example.com"],
        latitude=27.7,
        longitude=85.3,
    )
    result = service.deduplicate([first, second])
    assert len(result) == 1
    assert result[0].emails == ["info@example.com"]
    assert (result[0].latitude, result[0].longitude) == (27.7, 85.3)


def test_distinct_cids_veto_shared_domain_and_phone():
    service = BusinessDeduplicationService()
    first = Business(
        name="Agency",
        serper_cid="123",
        website="https://example.com",
        phone_numbers=["+12025550123"],
    )
    second = Business(
        name="Agency",
        serper_cid="456",
        website="https://example.com",
        phone_numbers=["+12025550123"],
    )
    assert len(service.deduplicate([first, second])) == 2


def test_same_cid_does_not_override_location_conflict():
    service = BusinessDeduplicationService()
    first = Business(name="Agency", serper_cid="123", city="London")
    second = Business(name="Agency", serper_cid="123", city="Paris")
    assert not service.are_duplicates(first, second)


def test_missing_cid_is_enriched_on_merge():
    service = BusinessDeduplicationService()
    first = Business(name="Agency", website="https://example.com")
    second = Business(name="Agency", website="https://example.com", serper_cid="123")
    assert service.merge_business(first, second).serper_cid == "123"


def test_search_distinct_cids_with_shared_domain():
    provider = Mock()
    provider.search_places.side_effect = [
        {
            "places": [
                {"title": "Agency", "cid": "123", "website": "https://example.com"}
            ]
        },
        {
            "places": [
                {"title": "Agency", "cid": "456", "website": "https://example.com"}
            ]
        },
    ]
    result = BusinessSearchService(provider).search_with_report(
        "agencies", max_results=2
    )
    assert [b.serper_cid for b in result.businesses] == ["123", "456"]


def test_resolve_preserves_original_metadata():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [
            {
                "title": "Agency",
                "cid": "123",
                "address": "Street",
                "website": "https://google.com/goto?url=a",
            }
        ],
        "credits": 1,
    }
    provider.resolve_links.return_value = {
        "places": [
            {"title": "Changed", "cid": "123", "website": "https://example.com"}
        ],
        "credits": 1,
    }
    result = BusinessSearchService(provider).search_with_report(
        "agencies", max_results=1
    )
    assert result.businesses[0].name == "Agency"
    assert result.businesses[0].address == "Street"
    assert result.businesses[0].website == "https://example.com"


def test_resolve_reordered_cids_are_rejected():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [
            {"title": "A", "cid": "123", "website": "https://google.com/goto?url=a"},
            {"title": "B", "cid": "456"},
        ],
        "credits": 1,
    }
    provider.resolve_links.return_value = {
        "places": [
            {"title": "B", "cid": "456"},
            {"title": "A", "cid": "123", "website": "https://example.com"},
        ],
        "credits": 1,
    }
    result = BusinessSearchService(provider).search_with_report(
        "agencies", max_results=2
    )
    assert result.businesses[0].website is None
    assert result.is_partial
    assert result.reported_credits == 2


def test_failed_page_marks_credit_tracking_incomplete():
    provider = Mock()
    provider.search_places.side_effect = [
        {"places": [{"title": "A"}], "credits": 1},
        requests.exceptions.Timeout(),
    ]
    result = BusinessSearchService(provider).search_with_report("agencies")
    assert result.reported_credits == 1
    assert result.unknown_credit_responses == 1
    assert not result.credit_tracking_complete


def test_failed_resolve_marks_credit_tracking_incomplete():
    provider = Mock()
    provider.search_places.return_value = {
        "places": [{"title": "A", "website": "https://google.com/goto?url=a"}],
        "credits": 1,
    }
    provider.resolve_links.side_effect = requests.exceptions.Timeout()
    result = BusinessSearchService(provider).search_with_report(
        "agencies", max_results=1
    )
    assert result.unknown_credit_responses == 1
    assert not result.credit_tracking_complete


def test_mapping_failure_marks_partial():
    provider = Mock()
    provider.search_places.side_effect = [
        {"places": [{"title": "A"}, None]},
        {"places": []},
    ]
    result = BusinessSearchService(provider).search_with_report("agencies")
    assert result.is_partial
