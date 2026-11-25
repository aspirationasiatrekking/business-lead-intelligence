from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import (
    map_serper_place,
    map_serper_places,
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
