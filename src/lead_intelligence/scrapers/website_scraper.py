import logging
import time
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.lead_intelligence.utils.secure_transport import (
    SecureHTTPTransport,
)
from src.lead_intelligence.utils.url_utils import (
    is_safe_url,
    is_valid_website,
)
from src.lead_intelligence.utils.website_policy import (
    is_candidate_business_website,
    same_website,
)

# =========================================================
# CONTACT PAGE CONFIGURATION
# =========================================================

CONTACT_KEYWORDS = {
    3: (
        "contact",
        "get in touch",
        "reach us",
        "kontakt",
        "contacto",
        "contatti",
        "联系我们",
        "お問い合わせ",
        "सम्पर्क",
        "संपर्क",
        "اتصل بنا",
    ),
    2: ("about", "enquiry", "inquiry", "support", "a propos", "über uns"),
    1: ("team", "company"),
}


@dataclass(frozen=True, slots=True)
class FetchedPage:
    html: str
    final_url: str


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
HEADERS.update(
    {
        "Accept": ("text/html,application/xhtml+xml,text/plain;q=0.8"),
        "Accept-Encoding": "identity",
    }
)

TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=15.0,
    write=5.0,
    pool=5.0,
)

MAX_REDIRECTS = 5

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_REQUEST_DURATION = 30.0

RESPONSE_CHUNK_SIZE = 64 * 1024

ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
)

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


class UnsupportedContentError(ValueError):
    """Raised when a response contains unsupported content."""


class DownloadDeadlineExceeded(ValueError):
    """Raised when the website download budget is exceeded."""


def check_download_deadline(deadline: float) -> None:
    """Reject requests that have exceeded their time budget."""

    if time.monotonic() >= deadline:
        raise DownloadDeadlineExceeded("Website download deadline exceeded")


def validate_response_headers(
    response: httpx.Response,
) -> None:
    """Validate response metadata before processing its body."""

    content_type = response.headers.get(
        "content-type",
        "",
    )

    media_type = content_type.split(";", 1)[0].strip().lower()

    # Some business websites omit Content-Type.
    if media_type and media_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedContentError(f"Unsupported content type: {media_type}")

    content_encoding = response.headers.get(
        "content-encoding",
        "",
    )

    encoding = content_encoding.strip().lower()

    if encoding not in {"", "identity"}:
        raise UnsupportedContentError("Compressed website responses are not supported")

    content_length = response.headers.get("content-length")

    if content_length is None:
        return

    content_length = content_length.strip()

    if not content_length.isascii() or not content_length.isdecimal():
        raise ValueError("Invalid Content-Length header")

    try:
        declared_size = int(content_length)

    except ValueError as error:
        raise ValueError("Invalid Content-Length header") from error

    if declared_size > MAX_RESPONSE_SIZE:
        raise ResponseTooLargeError("Website response exceeds allowed size")


def read_response_html(
    response: httpx.Response,
    deadline: float,
) -> str:
    """Read a bounded, uncompressed website response."""

    check_download_deadline(deadline)

    validate_response_headers(response)

    content = bytearray()

    for chunk in response.iter_bytes(chunk_size=RESPONSE_CHUNK_SIZE):
        check_download_deadline(deadline)

        if len(content) + len(chunk) > MAX_RESPONSE_SIZE:
            raise ResponseTooLargeError("Website response exceeded allowed size")

        content.extend(chunk)

    check_download_deadline(deadline)

    encoding = response.encoding or "utf-8"

    try:
        return bytes(content).decode(
            encoding,
            errors="replace",
        )

    except (LookupError, UnicodeError):
        return bytes(content).decode(
            "utf-8",
            errors="replace",
        )


# =========================================================
# RETRY CONFIGURATION
# =========================================================


def should_retry(error: BaseException) -> bool:
    """Retry only failures that may be temporary."""

    if isinstance(
        error,
        (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    if isinstance(
        error,
        httpx.HTTPStatusError,
    ):
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


def validate_redirect_destination(
    current_url: str,
    location: str,
) -> str:
    """Resolve and validate an HTTP redirect destination."""

    if not isinstance(location, str):
        raise ValueError("Invalid redirect destination")

    if not location.strip():
        raise ValueError("Redirect without destination")

    if "\\" in location or any(
        ord(character) < 32 or ord(character) == 127 for character in location
    ):
        raise ValueError("Invalid redirect characters")

    next_url = urljoin(
        current_url,
        location.strip(),
    )

    if not is_valid_website(next_url):
        raise ValueError("Invalid redirect URL")

    current = urlparse(current_url)
    destination = urlparse(next_url)

    if current.scheme == "https" and destination.scheme == "http":
        raise ValueError("HTTPS downgrade redirect is not allowed")

    if not is_safe_url(next_url):
        raise ValueError("Unsafe redirect destination")

    return urlunparse(destination._replace(fragment=""))


def create_secure_client() -> httpx.Client:
    """Create an HTTP client with outbound destination protection."""
    return httpx.Client(
        transport=SecureHTTPTransport(),
        headers=HEADERS,
        timeout=TIMEOUT,
        follow_redirects=False,
        trust_env=False,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=2,
        max=8,
    ),
    retry=retry_if_exception(should_retry),
    reraise=True,
)
def _request_website_html(url: str, *, business_only: bool = False) -> FetchedPage:
    """Fetch and validate website HTML securely."""

    deadline = time.monotonic() + MAX_REQUEST_DURATION

    if business_only and not is_candidate_business_website(url):
        raise ValueError("Third-party website is not allowed")

    if not is_safe_url(url):
        raise ValueError("Unsafe website URL")

    check_download_deadline(deadline)

    current_url = url.strip()

    with create_secure_client() as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            check_download_deadline(deadline)

            with client.stream(
                "GET",
                current_url,
            ) as response:
                check_download_deadline(deadline)

                if response.status_code in REDIRECT_STATUS_CODES:
                    if redirect_count >= MAX_REDIRECTS:
                        raise ValueError("Maximum redirect limit exceeded")

                    location = response.headers.get(
                        "location",
                        "",
                    )

                    current_url = validate_redirect_destination(
                        current_url,
                        location,
                    )

                    if business_only and not same_website(url, current_url):
                        raise ValueError("Cross-site business redirect")

                    check_download_deadline(deadline)

                else:
                    response.raise_for_status()

                    return FetchedPage(
                        html=read_response_html(response, deadline),
                        final_url=current_url,
                    )

    raise ValueError("Maximum redirect limit exceeded")


# =========================================================
# PUBLIC WEBSITE FETCHING FUNCTIONS
# =========================================================


def fetch_website_page(url: str, *, business_only: bool = False) -> FetchedPage | None:
    """Fetch website HTML and handle final request failures."""

    try:
        return _request_website_html(url, business_only=business_only)

    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        ValueError,
        ResponseTooLargeError,
    ) as error:
        logging.getLogger(__name__).warning(
            "Website fetch failed (%s)", type(error).__name__
        )

        return None


def fetch_website_html(url: str) -> str | None:
    page = fetch_website_page(url)
    return page.html if page is not None else None


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

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )


# =========================================================
# CONTACT PAGE DISCOVERY
# =========================================================


def contact_page_score(text: str) -> int:
    normalized = " ".join(
        "".join(
            c if unicodedata.category(c)[0] in {"L", "M", "N"} else " "
            for c in unquote(text).casefold()
        ).split()
    )
    return max(
        (
            score
            for score, words in CONTACT_KEYWORDS.items()
            if any(f" {word} " in f" {normalized} " for word in words)
        ),
        default=0,
    )


def find_contact_pages(url: str, html: str) -> list[str]:
    """Rank same-site contact links without following external links."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "template"]):
        element.decompose()
    pages = {}
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        if any(ord(c) < 32 or ord(c) == 127 for c in href) or "\\" in href:
            continue
        try:
            full_url = urljoin(url, href.strip())
            if not same_website(url, full_url):
                continue
            parsed = urlparse(full_url)
            full_url = urlunparse(parsed._replace(fragment=""))
            key = normalize_page_url(full_url)
            if key == normalize_page_url(url):
                continue
        except ValueError:
            continue
        text = link.get_text(" ", strip=True)
        score = max(contact_page_score(text), contact_page_score(parsed.path))
        if score and (key not in pages or score > pages[key][1]):
            pages[key] = (full_url, score)
    return [url for url, _ in sorted(pages.values(), key=lambda p: -p[1])]
