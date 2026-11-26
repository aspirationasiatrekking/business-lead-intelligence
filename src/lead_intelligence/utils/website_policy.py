from urllib.parse import urlparse

from src.lead_intelligence.utils.url_utils import is_valid_website

# Known third-party platforms, not proof of website ownership.
BLOCKED_DOMAINS = frozenset(
    {
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "tripadvisor.com",
        "booking.com",
        "expedia.com",
        "yelp.com",
        "google.com",
        "youtu.be",
        "youtube.com",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "wa.me",
        "whatsapp.com",
        "linktr.ee",
        "getyourguide.com",
        "viator.com",
    }
)


def is_candidate_business_website(url: str | None) -> bool:
    if not is_valid_website(url):
        return False
    host = urlparse(url.strip()).hostname.rstrip(".").lower()
    return not any(
        host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS
    )


def same_website(first: str, second: str) -> bool:
    if not all(is_candidate_business_website(url) for url in (first, second)):
        return False
    a, b = urlparse(first), urlparse(second)
    return (
        a.hostname.rstrip(".").lower().removeprefix("www.")
        == b.hostname.rstrip(".").lower().removeprefix("www.")
        and (a.port or (443 if a.scheme == "https" else 80)) in {80, 443}
        and (b.port or (443 if b.scheme == "https" else 80)) in {80, 443}
        and not (a.scheme == "https" and b.scheme == "http")
    )
