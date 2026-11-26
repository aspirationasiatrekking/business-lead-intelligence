import socket
import ssl
from unittest.mock import Mock, patch

import httpcore
import httpx
import pytest

from src.lead_intelligence.scrapers.website_scraper import (
    fetch_website_html,
)
from src.lead_intelligence.utils.secure_transport import (
    SecureHTTPTransport,
    SecureNetworkBackend,
    UnsafeDestinationError,
)

MODULE = "src.lead_intelligence.utils.secure_transport"


def make_stream(peer_ip="8.8.8.8", port=443):
    stream = Mock(spec=httpcore.NetworkStream)

    stream.get_extra_info.return_value = (
        peer_ip,
        port,
    )

    return stream


def test_connects_using_validated_numeric_ip():
    backend = SecureNetworkBackend()
    stream = make_stream()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ) as mock_resolve,
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ) as mock_connect,
    ):
        result = backend.connect_tcp(
            host="example.com",
            port=443,
            timeout=5,
        )

    mock_resolve.assert_called_once_with(
        hostname="example.com",
        port=443,
    )

    assert mock_connect.call_args.kwargs["host"] == ("8.8.8.8")

    assert mock_connect.call_args.kwargs["port"] == 443
    assert result is stream


def test_never_connects_using_unvalidated_hostname():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=make_stream(),
        ) as mock_connect,
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    assert mock_connect.call_args.kwargs["host"] != ("example.com")


@pytest.mark.parametrize(
    "port",
    [
        22,
        25,
        5432,
        6379,
        8080,
        8443,
    ],
)
def test_rejects_disallowed_ports_before_resolution(
    port,
):
    backend = SecureNetworkBackend()

    with (
        patch(f"{MODULE}.resolve_public_addresses") as mock_resolve,
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=port,
        )

    mock_resolve.assert_not_called()
    mock_connect.assert_not_called()


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "10.0.0.1",
        "::1",
        "fd00::1",
        "224.0.0.1",
    ],
)
def test_rejects_non_public_addresses_before_connection(
    address,
):
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(address,),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    mock_connect.assert_not_called()


def test_rejects_mixed_address_collection_before_connection():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(
                "8.8.8.8",
                "192.168.1.1",
            ),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    mock_connect.assert_not_called()


def test_handles_dns_resolution_failure():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            side_effect=ValueError("DNS failed"),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(
            UnsafeDestinationError,
            match="DNS failed",
        ),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    mock_connect.assert_not_called()


def test_rejects_empty_resolved_addresses():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    mock_connect.assert_not_called()


def test_closes_connection_to_private_peer():
    backend = SecureNetworkBackend()
    stream = make_stream(peer_ip="127.0.0.1")

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ),
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    stream.close.assert_called_once()


def test_closes_connection_to_unexpected_public_peer():
    backend = SecureNetworkBackend()
    stream = make_stream(peer_ip="1.1.1.1")

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ),
        pytest.raises(
            UnsafeDestinationError,
            match="does not match",
        ),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    stream.close.assert_called_once()


def test_closes_connection_when_peer_is_unavailable():
    backend = SecureNetworkBackend()
    stream = make_stream()

    stream.get_extra_info.return_value = None

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ),
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    stream.close.assert_called_once()


def test_falls_back_to_another_validated_address():
    backend = SecureNetworkBackend()

    stream = make_stream(peer_ip="1.1.1.1")

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(
                "8.8.8.8",
                "1.1.1.1",
            ),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            side_effect=[
                httpcore.ConnectError("Connection failed"),
                stream,
            ],
        ) as mock_connect,
    ):
        result = backend.connect_tcp(
            host="example.com",
            port=443,
        )

    assert result is stream
    assert mock_connect.call_count == 2

    assert [call.kwargs["host"] for call in mock_connect.call_args_list] == [
        "8.8.8.8",
        "1.1.1.1",
    ]


def test_raises_connection_error_when_all_addresses_fail():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(
                "8.8.8.8",
                "1.1.1.1",
            ),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            side_effect=httpcore.ConnectError("Connection failed"),
        ) as mock_connect,
        pytest.raises(httpcore.ConnectError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    assert mock_connect.call_count == 2


def test_rejects_connection_when_timeout_is_exhausted():
    backend = SecureNetworkBackend()

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch(
            f"{MODULE}.time.monotonic",
            side_effect=[0, 6],
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(httpcore.ConnectTimeout),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
            timeout=5,
        )

    mock_connect.assert_not_called()


def test_rejects_unix_socket_connections():
    backend = SecureNetworkBackend()

    with pytest.raises(
        UnsafeDestinationError,
        match="Unix socket",
    ):
        backend.connect_unix_socket(path="/tmp/example.sock")


def test_supports_public_ipv6_connections():
    backend = SecureNetworkBackend()

    address = "2606:4700:4700::1111"

    stream = make_stream(peer_ip=address)

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=(address,),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ) as mock_connect,
    ):
        result = backend.connect_tcp(
            host="example.com",
            port=443,
        )

    assert result is stream
    assert mock_connect.call_args.kwargs["host"] == address


def test_transport_uses_secure_network_backend():
    transport = SecureHTTPTransport()

    try:
        assert isinstance(
            transport._pool._network_backend,
            SecureNetworkBackend,
        )

    finally:
        transport.close()


def test_transport_preserves_tls_verification():
    transport = SecureHTTPTransport()

    try:
        context = transport._pool._ssl_context

        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True

    finally:
        transport.close()


def test_transport_is_compatible_with_httpx_client():
    transport = SecureHTTPTransport()

    with httpx.Client(
        transport=transport,
        trust_env=False,
    ) as client:
        assert isinstance(
            client,
            httpx.Client,
        )


def test_dns_rebinding_is_rejected_at_connection_boundary():
    backend = SecureNetworkBackend()

    # Preliminary validation may have succeeded earlier.
    # The connection-level resolution must still be safe.
    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            side_effect=ValueError("Hostname resolves to a non-public IP"),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
        pytest.raises(UnsafeDestinationError),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    mock_connect.assert_not_called()


def test_https_request_preserves_original_tls_hostname():
    stream = make_stream(
        peer_ip="8.8.8.8",
        port=443,
    )

    stream.start_tls.return_value = stream

    stream.get_extra_info.side_effect = lambda key: {
        "server_addr": ("8.8.8.8", 443),
        "ssl_object": None,
        "is_readable": False,
    }.get(key)

    stream.read.return_value = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html\r\n"
        b"Content-Length: 15\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        b"<html>OK</html>"
    )

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ) as mock_connect,
        httpx.Client(
            transport=SecureHTTPTransport(),
            trust_env=False,
        ) as client,
    ):
        response = client.get("https://example.com/contact")

    assert response.status_code == 200
    assert response.text == "<html>OK</html>"

    assert mock_connect.call_args.kwargs["host"] == ("8.8.8.8")

    tls_arguments = stream.start_tls.call_args.kwargs

    assert tls_arguments["server_hostname"] == ("example.com")

    context = tls_arguments["ssl_context"]

    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED

    request_bytes = b"".join(call.args[0] for call in stream.write.call_args_list)

    assert b"host: example.com" in request_bytes.lower()


def test_scraper_blocks_dns_rebinding_before_tcp_connection():
    public_result = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443),
        )
    ]

    private_result = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.1", 443),
        )
    ]

    with (
        patch(
            "src.lead_intelligence.utils.url_utils.socket.getaddrinfo",
            side_effect=[
                public_result,
                private_result,
            ],
        ) as mock_dns,
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
        ) as mock_connect,
    ):
        result = fetch_website_html("https://example.com")

    assert result is None
    assert mock_dns.call_count == 2

    mock_connect.assert_not_called()


def test_closes_connection_to_unexpected_peer_port():
    backend = SecureNetworkBackend()

    stream = make_stream(
        peer_ip="8.8.8.8",
        port=8080,
    )

    with (
        patch(
            f"{MODULE}.resolve_public_addresses",
            return_value=("8.8.8.8",),
        ),
        patch.object(
            httpcore.SyncBackend,
            "connect_tcp",
            return_value=stream,
        ),
        pytest.raises(
            UnsafeDestinationError,
            match="port does not match",
        ),
    ):
        backend.connect_tcp(
            host="example.com",
            port=443,
        )

    stream.close.assert_called_once()
