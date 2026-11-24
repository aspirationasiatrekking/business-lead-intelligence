
import httpx

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from src.lead_intelligence.utils.url_utils import is_safe_url


# =========================================================
# CONTACT PAGE CONFIGURATION
# =========================================================

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


# =========================================================
# HTTP CONFIGURATION
# =========================================================

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
    pool=5.0,
)

MAX_REDIRECTS = 5

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB

REDIRECT_STATUS_CODES = {
    301,
    302,
    303,
    307,
    308,
}


# =========================================================
# CUSTOM EXCEPTIONS
# =========================================================

class ResponseTooLargeError(Exception):
    """Raised when a website response exceeds the allowed size."""


# =========================================================
# RETRY CONFIGURATION
# =========================================================

def should_retry(error: BaseException) -> bool:
    """Determine whether an HTTP failure should be retried."""

    if isinstance(
        error,
        (httpx.TimeoutException, httpx.TransportError),
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


# =========================================================
# WEBSITE HTTP REQUEST
# =========================================================

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception(should_retry),
    reraise=True,
)
def _request_website_html(url: str) -> str:
    """Fetch website HTML with retries, safe redirects and size limits."""

    if not is_safe_url(url):
        raise ValueError(f"Unsafe website URL: {url}")

    current_url = url

    for redirect_count in range(MAX_REDIRECTS + 1):

        redirect_url = None

        with httpx.stream(
            "GET",
            current_url,
            headers=HEADERS,
            timeout=TIMEOUT,
            follow_redirects=False,
        ) as response:

            # -------------------------------------------------
            # HANDLE REDIRECTS
            # -------------------------------------------------

            if response.status_code in REDIRECT_STATUS_CODES:

                location = response.headers.get("location")

                if not location:
                    raise ValueError(
                        f"Redirect without destination: {current_url}"
                    )

                if redirect_count >= MAX_REDIRECTS:
                    raise ValueError(
                        "Maximum redirect limit exceeded"
                    )

                next_url = urljoin(current_url, location)

                if not is_safe_url(next_url):
                    raise ValueError(
                        f"Unsafe redirect destination: {next_url}"
                    )

                redirect_url = next_url

            else:

                # -------------------------------------------------
                # CHECK HTTP STATUS
                # -------------------------------------------------

                response.raise_for_status()

                # -------------------------------------------------
                # CHECK CONTENT LENGTH
                # -------------------------------------------------

                content_length = response.headers.get("content-length")

                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as error:
                        raise ValueError(
                            "Invalid Content-Length header"
                        ) from error

                    if declared_size < 0:
                        raise ValueError(
                            "Invalid negative Content-Length"
                        )

                    if declared_size > MAX_RESPONSE_SIZE:
                        raise ResponseTooLargeError(
                            "Website response exceeds 5 MB"
                        )

                # -------------------------------------------------
                # STREAM RESPONSE IN SMALL CHUNKS
                # -------------------------------------------------

                content = bytearray()

                for chunk in response.iter_bytes(
                    chunk_size=64 * 1024
                ):

                    content.extend(chunk)

                    if len(content) > MAX_RESPONSE_SIZE:
                        raise ResponseTooLargeError(
                            "Website response exceeded 5 MB"
                        )

                # Decode downloaded content
                encoding = response.encoding or "utf-8"

                return bytes(content).decode(
                    encoding,
                    errors="replace",
                )

        # Follow validated redirect after closing the response
        if redirect_url is not None:
            current_url = redirect_url

    raise ValueError("Maximum redirect limit exceeded")


# =========================================================
# PUBLIC WEBSITE FETCHING FUNCTIONS
# =========================================================

def fetch_website_html(url: str) -> str | None:
    """Fetch website HTML and handle final request failures."""

    try:
        return _request_website_html(url)

    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        ValueError,
        ResponseTooLargeError,
    ) as error:

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


# =========================================================
# URL NORMALIZATION
# =========================================================

def normalize_page_url(url: str) -> str:
    """Normalize URLs for duplicate detection."""

    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        "",
        "",
        "",
    ))


# =========================================================
# CONTACT PAGE DISCOVERY
# =========================================================

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

    return [
        page["url"]
        for page in sorted_pages
    ]
