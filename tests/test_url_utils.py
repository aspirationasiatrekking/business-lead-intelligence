import pytest

from src.lead_intelligence.utils.url_utils import (
    is_valid_hostname,
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


@pytest.mark.parametrize(
    "url",
    [
        123,
        True,
        [],
        {},
        b"https://example.com",
        "https://",
        "https://localhost",
        "https://example..com",
        "https://-example.com",
        "https://example-.com",
        "https://exam_ple.com",
        "https://example.com:",
        "https://example.com:0",
        "https://example.com:99999",
        "https://example.com:invalid",
        "https://user@example.com",
        "https://user:password@example.com",
        "https://example.com\\contact",
        "https://exam ple.com",
        "https://example.com/contact us",
        "https://exam\nple.com",
        "https://exam\tple.com",
        "https://example.com/\x00",
        "https://[invalid",
        "https://%65xample.com",
        "https://[fe80::1%25eth0]",
    ],
)
def test_rejects_unsafe_or_malformed_url_syntax(url):
    assert is_valid_website(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com",
        "https://sub.example.com",
        "https://example-domain.com",
        "https://example123.com",
        "https://example.com:443",
        "http://example.com:80",
        "https://8.8.8.8",
        "https://[2606:4700:4700::1111]",
        "https://bücher.de",
        "https://example.com/contact%20us",
    ],
)
def test_accepts_valid_website_syntax(url):
    assert is_valid_website(url) is True


@pytest.mark.parametrize(
    "hostname",
    [
        "example.com",
        "sub.example.com",
        "example.com.",
        "bücher.de",
        "8.8.8.8",
        "2606:4700:4700::1111",
    ],
)
def test_valid_hostname(hostname):
    assert is_valid_hostname(hostname) is True


@pytest.mark.parametrize(
    "hostname",
    [
        None,
        123,
        "",
        ".",
        "localhost",
        "-example.com",
        "example-.com",
        "example..com",
        "exam_ple.com",
        "example com",
        "%65xample.com",
        "a" * 64 + ".com",
        "fe80::1%eth0",
    ],
)
def test_invalid_hostname(hostname):
    assert is_valid_hostname(hostname) is False


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://bücher.de/",
            "https://xn--bcher-kva.de",
        ),
        (
            "https://EXAMPLE.COM./",
            "https://example.com",
        ),
        (
            "https://example.com:443/",
            "https://example.com:443",
        ),
        (
            "https://[2606:4700:4700::1111]/",
            "https://[2606:4700:4700::1111]",
        ),
    ],
)
def test_normalization_preserves_valid_host_information(
    url,
    expected,
):
    assert normalize_website_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        123,
        True,
        [],
        {},
        "https://exam ple.com",
        "https://example.com:0",
    ],
)
def test_normalization_rejects_invalid_inputs(url):
    assert normalize_website_url(url) is None
