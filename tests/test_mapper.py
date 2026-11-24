
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import (
    map_serper_place,
    map_serper_places,
)



def test_map_complete_serper_place():
    place = {
        "title": "Nepal Hiking Team",
        "address": "Thamel, Kathmandu, Nepal",
        "phoneNumber": "+977123456789",
        "website": "https://www.nepalhikingteam.com/",
        "category": "Tour operator"
    }

    business = map_serper_place(place)

    assert business.name == "Nepal Hiking Team"
    assert business.address == "Thamel, Kathmandu, Nepal"
    assert business.phone == "+977123456789"
    assert business.website == "https://www.nepalhikingteam.com"
    assert business.category == "Tour operator"


def test_map_serper_place_with_missing_fields():
    place = {
        "title": "Nepal Hiking Team"
    }

    business = map_serper_place(place)

    assert business.name == "Nepal Hiking Team"
    assert business.address is None
    assert business.phone is None
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
