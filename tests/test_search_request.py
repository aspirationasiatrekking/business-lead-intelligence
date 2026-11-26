from dataclasses import FrozenInstanceError

import pytest

from src.lead_intelligence.models.search_request import (
    SearchRequest,
)


def create_request(**overrides):
    values = {
        "country_code": "NP",
        "city": "Kathmandu",
        "query": "Trekking companies",
        "max_results": 10,
    }

    values.update(overrides)

    return SearchRequest(**values)


def test_creates_valid_search_request():
    request = create_request()

    assert request.country_code == "NP"
    assert request.city == "Kathmandu"
    assert request.query == "Trekking companies"
    assert request.max_results == 10


@pytest.mark.parametrize(
    "country_code",
    ["np", "NP", "Np", " np "],
)
def test_normalizes_country_code(country_code):
    request = create_request(country_code=country_code)

    assert request.country_code == "NP"


@pytest.mark.parametrize(
    ("country_code", "country_name"),
    [
        ("NP", "Nepal"),
        ("IN", "India"),
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("DE", "Germany"),
        ("AU", "Australia"),
        ("JP", "Japan"),
    ],
)
def test_resolves_country_name(
    country_code,
    country_name,
):
    request = create_request(country_code=country_code)

    assert request.country_name == country_name


@pytest.mark.parametrize(
    "country_code",
    [
        "",
        "NPL",
        "123",
        "XX",
        "ZZ",
        "UK",
        None,
    ],
)
def test_rejects_invalid_country(country_code):
    with pytest.raises((ValueError, TypeError)):
        create_request(country_code=country_code)


def test_normalizes_city_and_query_whitespace():
    request = create_request(
        city="  New   York  ",
        query="  Travel   agencies  ",
    )

    assert request.city == "New York"

    assert request.query == "Travel agencies"


@pytest.mark.parametrize(
    "city",
    [
        "",
        " ",
        None,
        123,
        "a" * 101,
        "Kathmandu\nPokhara",
        "City\x00",
    ],
)
def test_rejects_invalid_city(city):
    with pytest.raises((ValueError, TypeError)):
        create_request(city=city)


@pytest.mark.parametrize(
    "query",
    [
        "",
        " ",
        None,
        123,
        "a" * 251,
        "Travel\nagencies",
        "Travel\x00",
    ],
)
def test_rejects_invalid_query(query):
    with pytest.raises((ValueError, TypeError)):
        create_request(query=query)


@pytest.mark.parametrize(
    "max_results",
    [
        0,
        -1,
        101,
        1.5,
        True,
        "10",
        None,
    ],
)
def test_rejects_invalid_result_limit(max_results):
    with pytest.raises((ValueError, TypeError)):
        create_request(max_results=max_results)


@pytest.mark.parametrize(
    "max_results",
    [1, 10, 50, 100],
)
def test_accepts_valid_result_limit(max_results):
    request = create_request(max_results=max_results)

    assert request.max_results == max_results


def test_default_result_limit():
    request = SearchRequest(
        country_code="NP",
        city="Kathmandu",
        query="Travel agencies",
    )

    assert request.max_results == 10


def test_constructs_location_aware_query():
    request = create_request(
        country_code="GB",
        city="London",
        query="Travel agencies",
    )

    assert request.search_query == ("Travel agencies in London, United Kingdom")


def test_generates_provider_country_code():
    request = create_request()

    assert request.provider_country == "np"


def test_generates_phone_region():
    request = create_request()

    assert request.phone_region == "NP"


def test_generates_normalized_search_signature():
    request = create_request(
        country_code="np",
        city=" KATHMANDU ",
        query=" Trekking  Companies ",
    )

    assert request.signature == (
        "NP",
        "kathmandu",
        "trekking companies",
    )


def test_equivalent_requests_share_signature():
    first = create_request(
        city="Kathmandu",
        query="Travel agencies",
    )

    second = create_request(
        country_code="np",
        city=" KATHMANDU ",
        query=" travel  AGENCIES ",
    )

    assert first.signature == second.signature


def test_max_results_does_not_change_signature():
    first = create_request(max_results=10)

    second = create_request(max_results=100)

    assert first.signature == second.signature


def test_different_cities_have_different_signatures():
    first = create_request(city="Kathmandu")

    second = create_request(city="Pokhara")

    assert first.signature != second.signature


def test_different_queries_have_different_signatures():
    first = create_request(query="Trekking companies")

    second = create_request(query="Expedition companies")

    assert first.signature != second.signature


def test_different_countries_have_different_signatures():
    first = create_request(country_code="NP")

    second = create_request(country_code="IN")

    assert first.signature != second.signature


def test_search_request_is_immutable():
    request = create_request()

    with pytest.raises(FrozenInstanceError):
        request.city = "Pokhara"


def test_supports_unicode_search_inputs():
    request = create_request(
        country_code="JP",
        city="東京",
        query="旅行会社",
    )

    assert request.city == "東京"

    assert request.query == "旅行会社"
