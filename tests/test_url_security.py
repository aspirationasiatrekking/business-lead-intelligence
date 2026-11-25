from unittest.mock import patch

import pytest

from src.lead_intelligence.utils.url_utils import (
    is_public_ip,
    is_safe_redirect,
    is_safe_url,
)


@pytest.mark.parametrize(
    "ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "2606:4700:4700::1111",
    ],
)
def test_is_public_ip_allows_public_addresses(ip):
    assert is_public_ip(ip) is True


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "192.168.1.1",
        "10.0.0.1",
        "169.254.169.254",
        "172.16.0.1",
        "0.0.0.0",
        "::1",
        "fe80::1",
    ],
)
def test_is_public_ip_rejects_non_public_addresses(ip):
    assert is_public_ip(ip) is False


def make_dns_result(ip):
    return (
        2,
        1,
        6,
        "",
        (ip, 443),
    )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_url_allows_domain_with_public_ip(mock_dns):
    mock_dns.return_value = [make_dns_result("93.184.216.34")]

    assert is_safe_url("https://example.com") is True


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_url_rejects_domain_with_private_ip(mock_dns):
    mock_dns.return_value = [make_dns_result("192.168.1.1")]

    assert is_safe_url("https://example.com") is False


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_url_rejects_domain_with_mixed_ips(mock_dns):
    mock_dns.return_value = [
        make_dns_result("93.184.216.34"),
        make_dns_result("127.0.0.1"),
    ]

    assert is_safe_url("https://example.com") is False


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_url_rejects_dns_failure(mock_dns):
    import socket

    mock_dns.side_effect = socket.gaierror("DNS failed")

    assert is_safe_url("https://example.com") is False


def test_is_safe_url_rejects_private_ip_literal():
    assert is_safe_url("http://127.0.0.1") is False


def test_is_safe_url_allows_public_ip_literal():
    assert is_safe_url("https://8.8.8.8") is True


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_redirect_checks_destination(mock_dns):
    mock_dns.return_value = [make_dns_result("93.184.216.34")]

    assert (
        is_safe_redirect(
            "https://example.com",
            "https://another-example.com",
        )
        is True
    )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_is_safe_redirect_rejects_private_destination(mock_dns):
    mock_dns.return_value = [make_dns_result("127.0.0.1")]

    assert (
        is_safe_redirect(
            "https://example.com",
            "http://127.0.0.1",
        )
        is False
    )
