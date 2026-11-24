from urllib.parse import urlparse,urlunparse

from src.lead_intelligence.search.serper_provider import is_google_redirect


def is_valid_website(url: str | None) -> bool:

    if url is None or url.strip() == "":
        return False

    url = url.strip()

    if is_google_redirect(url):
        return False

    parsed_url = urlparse(url)

    if parsed_url.scheme not in ["http", "https"]:
        return False

    if not parsed_url.hostname:
        return False

    return True


def normalize_website_url(url: str | None) -> str | None:

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