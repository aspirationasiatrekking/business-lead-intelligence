
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)


CONTACT_KEYWORDS = {
    "contact",
    "contact-us",
    "about",
    "about-us",
    "reach-us",
    "get-in-touch",
    "get in touch",
    "our-team",
    "team",
    "company",
    "support",
    "enquiry",
    "inquiry",
}

HIGH_PRIORITY_KEYWORDS = {
    "contact",
    "contact-us",
    "get-in-touch",
    "reach-us",
    "about",
    "about-us",
}


# HTTP configuration
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=15.0,
    write=5.0,
    pool=5.0
)


def should_retry(error: BaseException) -> bool:
    """Determine whether an HTTP failure should be retried."""

    if isinstance(
        error,
        (httpx.TimeoutException, httpx.TransportError)
    ):
        return True

    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {
            429,
            500,
            502,
            503,
            504,
        }

    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception(should_retry),
    reraise=True,
)
def _request_website_html(url: str) -> str:
    """Fetch website HTML with automatic retries."""

    response = httpx.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
    )

    response.raise_for_status()

    return response.text


def fetch_website_html(url: str) -> str | None:
    """Fetch website HTML and handle final request failures."""

    try:
        return _request_website_html(url)

    except (httpx.HTTPError, httpx.InvalidURL) as error:
        print(f"Error fetching website {url}: {error}")
        return None


def extract_website_text(html: str) -> str:
    """Extract readable text from website HTML."""

    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    return soup.get_text(separator="\n", strip=True)


def fetch_website(url: str) -> str | None:
    """Fetch a website and return its readable text."""

    html = fetch_website_html(url)

    if html is None:
        return None

    return extract_website_text(html)


def normalize_page_url(url: str) -> str:
    """Normalize URLs for duplicate detection."""

    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        "",
        "",
        ""
    ))


def find_contact_pages(url: str, html: str) -> list[str]:
    """Discover and prioritize contact-related pages."""

    soup = BeautifulSoup(html, "html.parser")

    homepage = urlparse(url)
    contact_pages = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]

        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)

        # Allow only HTTP and HTTPS
        if parsed_url.scheme not in {"http", "https"}:
            continue

        # Only allow links from the same website
        if parsed_url.netloc.lower() != homepage.netloc.lower():
            continue

        # Ignore the homepage itself
        if parsed_url.path.rstrip("/") == homepage.path.rstrip("/"):
            continue

        link_text = link.get_text(" ", strip=True).lower()
        path = parsed_url.path.lower()

        searchable_text = f"{link_text} {path}"

        # Normalize separators
        normalized_text = searchable_text.replace("_", " ")
        normalized_text = normalized_text.replace("-", " ")

        # Calculate priority score
        score = 0

        for keyword in CONTACT_KEYWORDS:
            normalized_keyword = keyword.replace("-", " ")

            if normalized_keyword in normalized_text:
                score = max(score, 1)

        for keyword in HIGH_PRIORITY_KEYWORDS:
            normalized_keyword = keyword.replace("-", " ")

            if normalized_keyword in normalized_text:
                score = 2
                break

        if score > 0:
            normalized_url = normalize_page_url(full_url)

            if normalized_url not in contact_pages:
                contact_pages[normalized_url] = {
                    "url": full_url,
                    "score": score,
                }
            else:
                contact_pages[normalized_url]["score"] = max(
                    contact_pages[normalized_url]["score"],
                    score,
                )

    # Sort highest priority pages first
    sorted_pages = sorted(
        contact_pages.values(),
        key=lambda item: item["score"],
        reverse=True,
    )

    return [page["url"] for page in sorted_pages]
