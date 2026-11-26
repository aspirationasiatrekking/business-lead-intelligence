import pytest

from src.lead_intelligence.utils.country_utils import (
    normalize_country_code,
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
