import socket
from unittest.mock import patch

import pytest

from src.lead_intelligence.utils.url_utils import (
    is_public_ip,
    is_safe_redirect,
    is_safe_url,
    resolve_public_addresses,
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


@pytest.mark.parametrize(
    "ip",
    [
        "0.0.0.0",
        "127.0.0.1",
        "127.255.255.255",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.0.1",
        "169.254.169.254",
        "100.64.0.1",
        "192.0.2.1",
        "198.51.100.1",
        "203.0.113.1",
        "198.18.0.1",
        "224.0.0.1",
        "239.255.255.250",
        "240.0.0.1",
        "255.255.255.255",
        "::",
        "::1",
        "fc00::1",
        "fd00::1",
        "fe80::1",
        "fec0::1",
        "ff02::1",
        "2001:db8::1",
        "::ffff:127.0.0.1",
        "::ffff:192.168.0.1",
        "64:ff9b::7f00:1",
        "2002:7f00:1::1",
        "fe80::1%eth0",
        "",
        "invalid",
        None,
        123,
    ],
)
def test_rejects_non_public_or_special_purpose_ips(ip):
    assert is_public_ip(ip) is False


@pytest.mark.parametrize(
    "ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "9.9.9.9",
        "2606:4700:4700::1111",
        "2001:4860:4860::8888",
        "::ffff:8.8.8.8",
    ],
)
def test_accepts_public_unicast_ips(ip):
    assert is_public_ip(ip) is True


@pytest.mark.parametrize(
    "port",
    [
        0,
        21,
        22,
        25,
        3306,
        5432,
        6379,
        8080,
        8443,
        65535,
    ],
)
@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_rejects_disallowed_ports_without_dns(
    mock_dns,
    port,
):
    assert is_safe_url(f"https://example.com:{port}") is False

    mock_dns.assert_not_called()


@pytest.mark.parametrize(
    ("url", "expected_port"),
    [
        ("https://example.com", 443),
        ("http://example.com", 80),
        ("https://example.com:443", 443),
        ("http://example.com:80", 80),
    ],
)
@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolves_allowed_destination_ports(
    mock_dns,
    url,
    expected_port,
):
    mock_dns.return_value = [make_dns_result("8.8.8.8")]

    assert is_safe_url(url) is True

    mock_dns.assert_called_once_with(
        "example.com",
        expected_port,
        type=socket.SOCK_STREAM,
    )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_returns_unique_public_addresses(
    mock_dns,
):
    mock_dns.return_value = [
        make_dns_result("8.8.8.8"),
        make_dns_result("1.1.1.1"),
        make_dns_result("8.8.8.8"),
    ]

    addresses = resolve_public_addresses(
        "example.com",
        443,
    )

    assert addresses == (
        "8.8.8.8",
        "1.1.1.1",
    )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_rejects_mixed_public_private_addresses(
    mock_dns,
):
    mock_dns.return_value = [
        make_dns_result("8.8.8.8"),
        make_dns_result("192.168.0.1"),
    ]

    with pytest.raises(
        ValueError,
        match="non-public IP",
    ):
        resolve_public_addresses(
            "example.com",
            443,
        )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_rejects_empty_dns_results(mock_dns):
    mock_dns.return_value = []

    with pytest.raises(
        ValueError,
        match="no addresses",
    ):
        resolve_public_addresses(
            "example.com",
            443,
        )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_handles_dns_errors(mock_dns):
    mock_dns.side_effect = socket.gaierror("DNS resolution failed")

    with pytest.raises(
        ValueError,
        match="Unable to resolve",
    ):
        resolve_public_addresses(
            "example.com",
            443,
        )


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_accepts_public_literal_without_dns(
    mock_dns,
):
    result = resolve_public_addresses(
        "8.8.8.8",
        443,
    )

    assert result == ("8.8.8.8",)

    mock_dns.assert_not_called()


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_rejects_private_literal_without_dns(
    mock_dns,
):
    with pytest.raises(ValueError):
        resolve_public_addresses(
            "127.0.0.1",
            443,
        )

    mock_dns.assert_not_called()


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_resolver_rejects_invalid_hostname_without_dns(
    mock_dns,
):
    with pytest.raises(
        ValueError,
        match="Invalid destination hostname",
    ):
        resolve_public_addresses(
            "invalid hostname",
            443,
        )

    mock_dns.assert_not_called()


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_rejects_ipv6_private_dns_destination(mock_dns):
    mock_dns.return_value = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            6,
            "",
            ("::1", 443, 0, 0),
        )
    ]

    assert is_safe_url("https://example.com") is False


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_accepts_ipv6_public_dns_destination(mock_dns):
    mock_dns.return_value = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            6,
            "",
            (
                "2606:4700:4700::1111",
                443,
                0,
                0,
            ),
        )
    ]

    assert is_safe_url("https://example.com") is True


@patch("src.lead_intelligence.utils.url_utils.socket.getaddrinfo")
def test_rejects_redirect_to_disallowed_port(mock_dns):
    assert (
        is_safe_redirect(
            "https://example.com",
            "https://example.com:6379",
        )
        is False
    )

    mock_dns.assert_not_called()
