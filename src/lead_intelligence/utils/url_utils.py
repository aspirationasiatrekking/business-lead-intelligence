import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

from src.lead_intelligence.search.serper_provider import is_google_redirect


def is_valid_website(url: str | None) -> bool:
    """Validate the basic structure of a website URL."""

    if not url or not url.strip():
        return False

    url = url.strip()

    if is_google_redirect(url):
        return False

    try:
        parsed_url = urlparse(url)

        if parsed_url.scheme.lower() not in {"http", "https"}:
            return False

        if not parsed_url.hostname:
            return False

        # Reject URLs containing embedded credentials.
        if parsed_url.username is not None:
            return False

        if parsed_url.password is not None:
            return False

        # Validate port format and range.
        _ = parsed_url.port

        return True

    except ValueError:
        return False


def normalize_website_url(url: str | None) -> str | None:
    """Normalize a website URL."""

    if not is_valid_website(url):
        return None

    try:
        parsed_url = urlparse(url.strip())

        scheme = parsed_url.scheme.lower()
        hostname = parsed_url.hostname.lower()

        # Preserve IPv6 formatting.
        if ":" in hostname:
            hostname = f"[{hostname}]"

        # Preserve an explicitly provided port.
        if parsed_url.port is not None:
            hostname = f"{hostname}:{parsed_url.port}"

        path = parsed_url.path.rstrip("/")

        return urlunparse((scheme, hostname, path, "", "", ""))

    except ValueError:
        return None


def is_public_ip(ip_address: str) -> bool:
    """Check whether an IP address is globally routable."""

    try:
        ip = ipaddress.ip_address(ip_address)
        return ip.is_global

    except ValueError:
        return False


def is_safe_url(url: str | None) -> bool:
    """
    Validate a URL and check all IP addresses associated
    with its hostname.

    Rejects URLs resolving to private or non-public IPs.
    """

    if not is_valid_website(url):
        return False

    try:
        parsed_url = urlparse(url.strip())

        hostname = parsed_url.hostname
        port = parsed_url.port

        if not hostname:
            return False

        # Handle direct IP addresses.
        try:
            ip = ipaddress.ip_address(hostname)

            return ip.is_global

        except ValueError:
            pass

        # Resolve domain names.
        if port is None:
            port = 443 if parsed_url.scheme.lower() == "https" else 80

        try:
            addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)

        except socket.gaierror:
            return False

        if not addresses:
            return False

        # Reject the hostname if ANY resolved IP is non-public.
        for address in addresses:
            resolved_ip = address[4][0]

            if not is_public_ip(resolved_ip):
                return False

        return True

    except (ValueError, OSError):
        return False


def is_safe_redirect(original_url: str, redirect_url: str) -> bool:
    """
    Validate a redirect destination.

    The destination must independently pass URL and
    public-IP validation.
    """

    if not is_valid_website(original_url):
        return False

    if not is_valid_website(redirect_url):
        return False

    return is_safe_url(redirect_url)
