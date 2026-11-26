import ipaddress
import time

import httpcore
import httpx

from src.lead_intelligence.utils.url_utils import (
    ALLOWED_DESTINATION_PORTS,
    is_public_ip,
    resolve_public_addresses,
)


class UnsafeDestinationError(ValueError):
    """Raised when an outbound connection violates security policy."""


class SecureNetworkBackend(httpcore.SyncBackend):
    """Establish connections only to validated public IP addresses."""

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ) -> httpcore.NetworkStream:
        if port not in ALLOWED_DESTINATION_PORTS:
            raise UnsafeDestinationError("Destination port is not allowed")

        started_at = time.monotonic()

        try:
            addresses = resolve_public_addresses(
                hostname=host,
                port=port,
            )

        except ValueError as error:
            raise UnsafeDestinationError(str(error)) from error

        if not addresses:
            raise UnsafeDestinationError("No public destination addresses available")

        # Validate the complete address collection before connecting.
        validated_addresses = []

        for address in addresses:
            if not is_public_ip(address):
                raise UnsafeDestinationError("Connection destination is not public")

            validated_addresses.append(str(ipaddress.ip_address(address)))

        last_error = None

        for address in validated_addresses:
            remaining_timeout = timeout

            if timeout is not None:
                elapsed = time.monotonic() - started_at
                remaining_timeout = timeout - elapsed

                if remaining_timeout <= 0:
                    raise httpcore.ConnectTimeout("Connection timeout exceeded")

            try:
                # Connect to the validated numeric IP, not the hostname.
                stream = super().connect_tcp(
                    host=address,
                    port=port,
                    timeout=remaining_timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )

            except (
                httpcore.ConnectError,
                httpcore.ConnectTimeout,
            ) as error:
                last_error = error
                continue

            try:
                peer = stream.get_extra_info("server_addr")

                if not peer:
                    raise UnsafeDestinationError(
                        "Unable to verify connection destination"
                    )

                peer_ip = ipaddress.ip_address(peer[0])
                expected_ip = ipaddress.ip_address(address)
                if peer[1] != port:
                    raise UnsafeDestinationError(
                        "Connected destination port does not match validated port"
                    )

                if not is_public_ip(str(peer_ip)):
                    raise UnsafeDestinationError("Connected destination is not public")

                if peer_ip != expected_ip:
                    raise UnsafeDestinationError(
                        "Connected destination does not match validated address"
                    )

            except Exception:
                stream.close()
                raise

            return stream

        if last_error is not None:
            raise last_error

        raise httpcore.ConnectError("Unable to connect to any validated destination")

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options=None,
    ) -> httpcore.NetworkStream:
        raise UnsafeDestinationError("Unix socket connections are not allowed")


class SecureHTTPTransport(httpx.HTTPTransport):
    """HTTPX transport with connection-level destination validation."""

    def __init__(self) -> None:
        super().__init__(
            verify=True,
            trust_env=False,
            http1=True,
            http2=False,
            retries=0,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=0,
            ),
        )

        original_pool = self._pool

        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(
                verify=True,
                trust_env=False,
            ),
            max_connections=10,
            max_keepalive_connections=0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=SecureNetworkBackend(),
        )

        original_pool.close()
