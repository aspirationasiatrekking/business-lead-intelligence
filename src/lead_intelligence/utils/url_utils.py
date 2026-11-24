
import ipaddress
from urllib.parse import urlparse, urlunparse

from src.lead_intelligence.search.serper_provider import is_google_redirect


def is_valid_website(url: str | None) -> bool:
    """Check whether a URL has a valid HTTP or HTTPS website format."""

    if url is None or url.strip() == "":
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

        # Validate the port if one is provided
        _ = parsed_url.port

        return True

    except ValueError:
        return False


def normalize_website_url(url: str | None) -> str | None:
    """Normalize a website URL."""

    if not is_valid_website(url):
        return None

    parsed_url = urlparse(url.strip())

    scheme = parsed_url.scheme.lower()
    hostname = parsed_url.hostname.lower()
    path = parsed_url.path.rstrip("/")

    normalized_url = urlunparse((
        scheme,
        hostname,
        path,
        "",
        "",
        ""
    ))

    return normalized_url


def is_safe_url(url: str | None) -> bool:
    """
    Check whether a URL uses a publicly routable IP address
    when its hostname is an IP literal.

    Domain names require DNS resolution checks, which will
    be implemented separately.
    """

    if not is_valid_website(url):
        return False

    try:
        parsed_url = urlparse(url.strip())
        hostname = parsed_url.hostname

        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # Domain names need DNS validation.
            return True

        return ip.is_global

    except ValueError:
        return False
