import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse

from src.lead_intelligence.search.serper_provider import is_google_redirect

ALLOWED_SCHEMES = frozenset({"http", "https"})

ALLOWED_DESTINATION_PORTS = frozenset({80, 443})

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
}

HOSTNAME_LABEL_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")

BLOCKED_IPV6_NETWORKS = (
    ipaddress.IPv6Network("2002::/16"),
    ipaddress.IPv6Network("2001::/32"),
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
)


def is_valid_hostname(hostname: str) -> bool:
    """Validate an IP literal or DNS hostname."""
    if not isinstance(hostname, str) or not hostname:
        return False

    # Reject scoped IPv6 addresses and encoded hostnames.
    if "%" in hostname:
        return False

    try:
        ipaddress.ip_address(hostname)
        return True

    except ValueError:
        pass

    try:
        ascii_hostname = hostname.rstrip(".").encode("idna").decode("ascii")

    except UnicodeError:
        return False

    if not ascii_hostname or len(ascii_hostname) > 253:
        return False

    labels = ascii_hostname.split(".")

    if len(labels) < 2:
        return False

    return all(HOSTNAME_LABEL_PATTERN.fullmatch(label) is not None for label in labels)


def is_valid_website(url: str | None) -> bool:
    """Validate website URL syntax without performing DNS requests."""
    if not isinstance(url, str):
        return False

    url = url.strip()

    if not url:
        return False

    # Reject ambiguous URL characters and embedded whitespace.
    if "\\" in url:
        return False

    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in url
    ):
        return False

    if is_google_redirect(url):
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False

        if not parsed.hostname:
            return False

        if parsed.username is not None:
            return False

        if parsed.password is not None:
            return False

        if parsed.netloc.endswith(":"):
            return False

        port = parsed.port

        if port is not None and port == 0:
            return False

        return is_valid_hostname(parsed.hostname)

    except (ValueError, UnicodeError):
        return False


def normalize_website_url(url: str | None) -> str | None:
    """Normalize a syntactically valid business website URL."""
    if not is_valid_website(url):
        return None

    try:
        parsed = urlparse(url.strip())

        scheme = parsed.scheme.lower()
        hostname = parsed.hostname.lower()

        if ":" in hostname:
            hostname = f"[{hostname}]"

        else:
            hostname = hostname.rstrip(".").encode("idna").decode("ascii")

        if parsed.port is not None:
            hostname = f"{hostname}:{parsed.port}"

        path = parsed.path.rstrip("/")

        return urlunparse(
            (
                scheme,
                hostname,
                path,
                "",
                "",
                "",
            )
        )

    except (ValueError, UnicodeError):
        return None


def is_public_ip(ip_address: str) -> bool:
    """Allow only globally routable, unicast IP addresses."""
    if not isinstance(ip_address, str):
        return False

    if "%" in ip_address:
        return False

    try:
        ip = ipaddress.ip_address(ip_address)

    except ValueError:
        return False

    if isinstance(ip, ipaddress.IPv6Address):
        # Evaluate IPv4-mapped IPv6 using the IPv4 address.
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))

        if ip.is_site_local:
            return False

        if any(ip in network for network in BLOCKED_IPV6_NETWORKS):
            return False

    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def resolve_public_addresses(
    hostname: str,
    port: int,
) -> tuple[str, ...]:
    """Resolve a hostname and reject any non-public destination."""
    if not is_valid_hostname(hostname):
        raise ValueError("Invalid destination hostname")

    if port not in ALLOWED_DESTINATION_PORTS:
        raise ValueError("Destination port is not allowed")

    try:
        literal_ip = ipaddress.ip_address(hostname)

    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if not is_public_ip(str(literal_ip)):
            raise ValueError("Non-public IP destination")

        return (str(literal_ip),)

    try:
        addresses = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )

    except OSError as error:
        raise ValueError("Unable to resolve destination hostname") from error

    if not addresses:
        raise ValueError("Destination hostname returned no addresses")

    public_addresses = []

    for address in addresses:
        resolved_ip = address[4][0]

        if not is_public_ip(resolved_ip):
            raise ValueError("Hostname resolves to a non-public IP")

        canonical_ip = str(ipaddress.ip_address(resolved_ip))

        if canonical_ip not in public_addresses:
            public_addresses.append(canonical_ip)

    return tuple(public_addresses)


def is_safe_url(url: str | None) -> bool:
    """Perform preliminary URL and DNS safety checks.

    This check alone does not prevent DNS rebinding.
    The HTTP connection must also use a validated address.
    """
    if not is_valid_website(url):
        return False

    try:
        parsed = urlparse(url.strip())

        port = parsed.port

        if port is None:
            port = DEFAULT_PORTS[parsed.scheme.lower()]

        resolve_public_addresses(
            parsed.hostname,
            port,
        )

        return True

    except (ValueError, OSError):
        return False


def is_safe_redirect(
    original_url: str,
    redirect_url: str,
) -> bool:
    """Perform preliminary validation of a redirect destination."""
    if not is_valid_website(original_url):
        return False

    return is_safe_url(redirect_url)
