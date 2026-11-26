import pytest

from src.lead_intelligence.utils.country_utils import (
    find_country_code,
    get_country_name,
    get_country_options,
    normalize_country_code,
    validate_country_code,
)


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("np", "np"),
        ("NP", "np"),
        ("Np", "np"),
        (" US ", "us"),
        ("gb", "gb"),
        ("\tIN\n", "in"),
        (None, None),
    ],
)
def test_normalize_country_code(country, expected):
    assert normalize_country_code(country) == expected


@pytest.mark.parametrize(
    "country",
    [
        "",
        " ",
        "N",
        "NPL",
        "123",
        "N1",
        "日本",
        "éé",
        "N P",
    ],
)
def test_normalize_country_code_rejects_invalid_values(
    country,
):
    with pytest.raises(
        ValueError,
        match="Country code must contain two ASCII letters",
    ):
        normalize_country_code(country)


@pytest.mark.parametrize(
    "country",
    [
        123,
        True,
        False,
        [],
        {},
        1.5,
    ],
)
def test_normalize_country_code_rejects_invalid_types(
    country,
):
    with pytest.raises(
        TypeError,
        match="Country code must be a string",
    ):
        normalize_country_code(country)


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("np", "NP"),
        ("US", "US"),
        ("gb", "GB"),
        (" IN ", "IN"),
        ("jp", "JP"),
    ],
)
def test_validate_country_code(
    country,
    expected,
):
    assert validate_country_code(country) == expected


@pytest.mark.parametrize(
    "country",
    [
        "",
        "XX",
        "ZZ",
        "NPL",
        "UK",
        "123",
        None,
    ],
)
def test_validate_country_code_rejects_unknown_country(
    country,
):
    with pytest.raises((ValueError, TypeError)):
        validate_country_code(country)


@pytest.mark.parametrize(
    ("country_code", "expected"),
    [
        ("NP", "Nepal"),
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("IN", "India"),
        ("JP", "Japan"),
    ],
)
def test_get_country_name(
    country_code,
    expected,
):
    assert get_country_name(country_code) == expected


@pytest.mark.parametrize(
    ("country_name", "expected"),
    [
        ("Nepal", "NP"),
        ("nepal", "NP"),
        (" Nepal ", "NP"),
        ("United States", "US"),
        ("United Kingdom", "GB"),
        ("India", "IN"),
        ("NP", "NP"),
        ("Japan", "JP"),
    ],
)
def test_find_country_code(
    country_name,
    expected,
):
    assert find_country_code(country_name) == expected


@pytest.mark.parametrize(
    "country_name",
    [
        None,
        "",
        " ",
        "Unknown country",
        123,
    ],
)
def test_find_country_code_handles_unknown_input(
    country_name,
):
    assert find_country_code(country_name) is None


def test_country_options_include_nepal():
    options = get_country_options()

    assert {
        "code": "NP",
        "name": "Nepal",
    } in options


def test_country_options_include_international_countries():
    options = get_country_options()

    codes = {option["code"] for option in options}

    assert {
        "NP",
        "US",
        "GB",
        "IN",
        "JP",
        "AU",
        "DE",
    }.issubset(codes)


def test_country_options_have_unique_codes():
    options = get_country_options()

    codes = [option["code"] for option in options]

    assert len(codes) == len(set(codes))


def test_country_options_are_sorted():
    options = get_country_options()

    names = [option["name"].casefold() for option in options]

    assert names == sorted(names)


def test_country_options_are_independent():
    first = get_country_options()

    first.clear()

    second = get_country_options()

    assert second
