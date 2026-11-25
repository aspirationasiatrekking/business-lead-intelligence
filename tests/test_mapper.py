from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import (
    map_serper_place,
    map_serper_places,
    map_serper_places_with_report,
)


def test_map_complete_serper_place():
    place = {
        "title": "Nepal Hiking Team",
        "address": "Thamel, Kathmandu, Nepal",
        "phoneNumber": "+9779846041887",
        "website": "https://www.nepalhikingteam.com/",
        "category": "Tour operator",
    }

    business = map_serper_place(place)

    assert business.name == "Nepal Hiking Team"
    assert business.address == "Thamel, Kathmandu, Nepal"
    assert business.phone_numbers == ["+9779846041887"]
    assert business.website == "https://www.nepalhikingteam.com"
    assert business.category == "Tour operator"


def test_map_serper_place_with_missing_fields():
    place = {"title": "Nepal Hiking Team"}

    business = map_serper_place(place)

    assert business.name == "Nepal Hiking Team"
    assert business.address is None
    assert business.phone_numbers == []
    assert business.website is None
    assert business.category is None


def test_map_multiple_serper_places():
    places = [
        {"title": "Business One"},
        {"title": "Business Two"},
        {"title": "Business Three"},
    ]

    businesses = map_serper_places(places)

    assert len(businesses) == 3
    assert all(isinstance(business, Business) for business in businesses)
    assert businesses[0].name == "Business One"
    assert businesses[1].name == "Business Two"
    assert businesses[2].name == "Business Three"


def test_map_empty_serper_places():
    businesses = map_serper_places([])

    assert businesses == []


def test_map_serper_place_normalizes_website():
    place = {
        "title": "Example Trekking",
        "website": "HTTPS://Example.com/",
    }

    business = map_serper_place(place)

    assert business.website == "https://example.com"


def test_map_serper_place_rejects_google_redirect():
    place = {
        "title": "Example Trekking",
        "website": "https://www.google.com/goto?url=abc",
    }

    business = map_serper_place(place)

    assert business.website is None


def test_map_serper_place_handles_missing_website():
    place = {
        "title": "Example Trekking",
    }

    business = map_serper_place(place)

    assert business.website is None


def test_map_serper_place_rejects_invalid_website():
    place = {
        "title": "Example Trekking",
        "website": "example.com",
    }

    business = map_serper_place(place)

    assert business.website is None


def test_map_serper_place_uses_website_domain_when_title_missing():
    place = {"website": "https://www.nepalhikingteam.com/"}

    business = map_serper_place(place)

    assert business.name == "nepalhikingteam.com"


def test_map_serper_place_without_title_or_valid_website():
    place = {"website": "invalid-url"}

    businesses = map_serper_places([place])

    assert businesses == []


def test_map_serper_place_normalizes_phone_using_selected_region():
    place = {
        "title": "Example Business",
        "phoneNumber": "2025550123",
    }

    business = map_serper_place(place, region="US")

    assert business.phone_numbers == ["+12025550123"]


def test_map_serper_places_passes_selected_region():
    places = [
        {
            "title": "Nepal Business",
            "phoneNumber": "9846041887",
        }
    ]

    businesses = map_serper_places(places, region="NP")

    assert businesses[0].phone_numbers == ["+9779846041887"]


def test_map_serper_places_with_report_tracks_successes_and_failures():
    places = [
        {"title": "Nepal Hiking Team"},
        {"website": "https://www.example.com"},
        {"website": "invalid-url"},
        {"title": "Another Trekking Company"},
    ]

    result = map_serper_places_with_report(places)

    assert len(result.businesses) == 3
    assert len(result.failures) == 1
    assert result.total_processed == 4

    assert result.businesses[0].name == "Nepal Hiking Team"
    assert result.businesses[1].name == "example.com"
    assert result.businesses[2].name == "Another Trekking Company"

    assert result.failures[0].item_index == 2
    assert result.failures[0].stage == "mapping"
    assert result.failures[0].message == (
        "Business has no usable name or valid website."
    )


def test_map_serper_places_with_report_handles_invalid_record_types():
    places = [
        {"title": "Valid Business"},
        "Invalid record",
        None,
        {"title": "Another Valid Business"},
    ]

    result = map_serper_places_with_report(places)

    assert len(result.businesses) == 2
    assert len(result.failures) == 2
    assert result.total_processed == 4

    assert result.failures[0].item_index == 1
    assert result.failures[1].item_index == 2


def test_map_serper_places_with_report_returns_empty_result():
    result = map_serper_places_with_report([])

    assert result.businesses == []
    assert result.failures == []
    assert result.total_processed == 0


def test_map_serper_places_with_report_continues_after_mapping_exception(
    monkeypatch,
):
    from src.lead_intelligence.models import mapper

    original_mapper = mapper.map_serper_place

    def mock_map_serper_place(place, region=None):
        if place.get("title") == "Broken Business":
            raise ValueError("Invalid business data")

        return original_mapper(place, region=region)

    monkeypatch.setattr(mapper, "map_serper_place", mock_map_serper_place)

    places = [
        {"title": "First Business"},
        {"title": "Broken Business"},
        {"title": "Third Business"},
    ]

    result = mapper.map_serper_places_with_report(places)

    assert len(result.businesses) == 2
    assert len(result.failures) == 1
    assert result.total_processed == 3

    assert result.businesses[0].name == "First Business"
    assert result.businesses[1].name == "Third Business"

    assert result.failures[0].item_index == 1
    assert result.failures[0].stage == "mapping"
    assert "Invalid business data" in result.failures[0].message
