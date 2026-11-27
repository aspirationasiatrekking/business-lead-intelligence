import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services import geographic_enrichment as geo


@pytest.fixture
def city_data(monkeypatch):
    index = {
        "kathmandu": (geo.CityPoint("Kathmandu", "NP", 27.70169, 85.3206),),
        "toronto": (geo.CityPoint("Toronto", "CA", 43.70011, -79.4163),),
    }
    monkeypatch.setattr(geo, "city_index", lambda: index)
    return index


@pytest.mark.parametrize(
    "address, latitude, longitude, city, code",
    [
        (
            "Marcopolo Complex, Ground Floor, Kathmandu 44600",
            27.710253,
            85.32199,
            "Kathmandu",
            "NP",
        ),
        ("ठमेल भगवती मार्ग, Kathmandu 44600", 27.716164, 85.31091, "Kathmandu", "NP"),
        ("Street, Toronto", 43.7, -79.42, "Toronto", "CA"),
        ("Street, Kathmandu 44600", 43.7, -79.42, None, None),
        ("Street, Kathmandu Road", 27.71, 85.32, None, None),
        (None, 27.71, 85.32, None, None),
        ("Street, Kathmandu", None, 85.32, None, None),
        ("Street, Kathmandu", 27.71, None, None, None),
    ],
)
def test_city_match(city_data, address, latitude, longitude, city, code):
    business = Business(
        name="Travel Agency", address=address, latitude=latitude, longitude=longitude
    )
    service = geo.GeographicEnrichmentService()
    service.enrich(business)
    assert business.city == city
    assert business.country_code == code
    assert business.district is None
    assert business.state is None
    service.enrich(business)
    if code:
        for field in ("city", "country", "country_code"):
            assert business.geographic_sources[field] == [geo.CITY_SOURCE]


def test_ambiguous_city(city_data):
    city_data["kathmandu"] += (geo.CityPoint("Kathmandu", "IN", 27.71, 85.32),)
    business = Business(
        name="Agency", address="Street, Kathmandu", latitude=27.71, longitude=85.32
    )
    geo.GeographicEnrichmentService().enrich(business)
    assert business.country_code is None
    assert business.city is None


def test_provider_conflict_preserved(city_data):
    business = Business(
        name="Agency",
        address="Street, Kathmandu",
        latitude=27.71,
        longitude=85.32,
        country_code="US",
        geographic_sources={"country_code": ["provider"]},
    )
    geo.GeographicEnrichmentService().enrich(business)
    assert business.country_code == "US"
    assert business.city is None
    assert business.geographic_conflicts
    assert business.geographic_sources["country_code"] == ["provider"]


def test_existing_conflict_blocks_inference(city_data):
    business = Business(
        name="Agency",
        address="Street, Kathmandu",
        latitude=27.71,
        longitude=85.32,
        geographic_conflicts=["Provider country name and code disagree"],
    )
    geo.GeographicEnrichmentService().enrich(business)
    assert business.country_code is None
    assert business.city is None


def test_real_geonames_dataset():
    business = Business(
        name="Agency",
        address="Street, Kathmandu 44600",
        latitude=27.710253,
        longitude=85.32199,
    )
    geo.GeographicEnrichmentService().enrich(business)
    assert (business.city, business.country_code) == ("Kathmandu", "NP")
