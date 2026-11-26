import pytest

from src.lead_intelligence.search.serper_provider import is_google_redirect


@pytest.mark.parametrize(
    "url",
    [
        "https://www.google.com/goto?url=example",
        "https://google.com/goto?url=example",
        "https://www.google.co/goto?url=example",
        "https://google.co/goto?url=example",
        "http://google.com/goto?url=example",
        "HTTPS://GOOGLE.COM/goto?url=example",
        "  https://google.com/goto?url=example  ",
    ],
)
def test_recognizes_supported_google_redirects(url):
    assert is_google_redirect(url) is True


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        " ",
        "\t",
        123,
        True,
        [],
        {},
        b"https://google.com/goto",
    ],
)
def test_rejects_invalid_redirect_input(url):
    assert is_google_redirect(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://[invalid",
        "https://[::1",
        "https://google.com:invalid/goto",
        "https://google.com:99999/goto",
    ],
)
def test_handles_malformed_redirect_urls(url):
    assert is_google_redirect(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/goto",
        "https://google.com.example.com/goto",
        "https://fakegoogle.com/goto",
        "https://google.com/contact",
        "https://google.com/goto/another",
        "https://google.com",
        "google.com/goto",
        "//google.com/goto",
        "ftp://google.com/goto",
        "javascript:google.com/goto",
    ],
)
def test_rejects_unsupported_redirect_urls(url):
    assert is_google_redirect(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://user@google.com/goto",
        "https://user:password@google.com/goto",
        "https://google.com@example.com/goto",
    ],
)
def test_rejects_redirect_urls_with_credentials(url):
    assert is_google_redirect(url) is False
