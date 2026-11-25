import pytest

from src.lead_intelligence.utils.url_utils import (
    is_valid_website,
    normalize_website_url,
)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com", True),
        ("http://example.com", True),
        (None, False),
        ("", False),
        ("example.com", False),
        ("https://www.google.com/goto?url=abc", False),
        ("ftp://example.com", False),
        ("https://", False),
        ("   https://example.com   ", True),
    ],
)
def test_is_valid_website(url, expected):
    assert is_valid_website(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("HTTPS://Example.com/", "https://example.com"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com//", "https://example.com"),
        ("https://example.com/about/", "https://example.com/about"),
        (
            "HTTPS://Example.com/about/?ref=google#team",
            "https://example.com/about",
        ),
        (None, None),
        ("", None),
        ("example.com", None),
        ("https://www.google.com/goto?url=abc", None),
        ("ftp://example.com", None),
    ],
)
def test_normalize_website_url(url, expected):
    assert normalize_website_url(url) == expected
