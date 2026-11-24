
import pytest

from src.lead_intelligence.utils.url_utils import is_safe_url


@pytest.mark.parametrize(
    "url",
    [
        "https://8.8.8.8",
        "https://1.1.1.1",
    ],
)
def test_is_safe_url_allows_public_ip_addresses(url):
    assert is_safe_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://169.254.169.254",
        "http://172.16.0.1",
        "http://0.0.0.0",
    ],
)
def test_is_safe_url_rejects_private_ip_addresses(url):
    assert is_safe_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "   ",
        "ftp://example.com",
        "not-a-valid-url",
        "http://",
    ],
)
def test_is_safe_url_rejects_invalid_urls(url):
    assert is_safe_url(url) is False


def test_is_safe_url_allows_domain_name():
    # DNS validation will be implemented in the next step.
    assert is_safe_url("https://example.com") is True
