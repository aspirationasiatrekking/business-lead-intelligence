
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from requests_ratelimiter import LimiterSession
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


load_dotenv()


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 30.0


def is_retryable_error(error: Exception) -> bool:
    """Determine whether a failed HTTP request should be retried."""

    if isinstance(
        error,
        (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ),
    ):
        return True

    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response

        return (
            response is not None
            and response.status_code in RETRYABLE_STATUS_CODES
        )

    return False


def get_retry_after_seconds(error: Exception) -> float | None:
    """Extract the Retry-After delay from an HTTP response."""

    if not isinstance(error, requests.exceptions.HTTPError):
        return None

    response = error.response

    if response is None or response.status_code != 429:
        return None

    retry_after = response.headers.get("Retry-After")

    if not retry_after:
        return None

    # Retry-After can contain a number of seconds.
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        pass

    # Or it can contain an HTTP date.
    try:
        retry_date = parsedate_to_datetime(retry_after)

        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=timezone.utc)

        delay = (
            retry_date - datetime.now(timezone.utc)
        ).total_seconds()

        return max(0.0, delay)

    except (TypeError, ValueError, OverflowError):
        return None


EXPONENTIAL_BACKOFF = wait_exponential(
    multiplier=1,
    min=1,
    max=8,
)


def wait_for_retry(retry_state) -> float:
    """Respect Retry-After, otherwise use exponential backoff."""

    error = retry_state.outcome.exception()

    retry_after = get_retry_after_seconds(error)

    if retry_after is not None:
        return min(retry_after, MAX_RETRY_AFTER_SECONDS)

    return EXPONENTIAL_BACKOFF(retry_state)


class SerperSearchProvider:

    BASE_URL = "https://google.serper.dev"

    REQUESTS_PER_SECOND = 1

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise ValueError("SERPER_API_KEY is missing from .env")

        self.session = LimiterSession(
            per_second=self.REQUESTS_PER_SECOND,
            burst=1,
            max_delay=30,
        )

    @retry(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(3),
        wait=wait_for_retry,
        reraise=True,
    )
    def _post(self, endpoint: str, payload: dict) -> dict:
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        response = self.session.post(
            f"{self.BASE_URL}/{endpoint}",
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def search_places(
        self,
        query: str,
        country: str | None = None,
        page: int = 1,
        num: int = 10,
    ) -> dict:

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if not isinstance(page, int) or isinstance(page, bool):
            raise ValueError("Page must be an integer")

        if page < 1:
            raise ValueError("Page must be greater than or equal to 1")
        
        if not isinstance(num, int) or isinstance(num, bool):
            raise ValueError("Number of results must be an integer")

        if not 1 <= num <= 100:
            raise ValueError("Number of results must be between 1 and 100")

        payload = {
            "q": query.strip(),
            "hl": "en",
            "page": page,
            "num": num,
        }

        if country:
            payload["gl"] = country

        return self._post("places", payload)

    def resolve_links(self, results: dict) -> dict:
        return self._post("resolve", results)

    def close(self):
        """Close the HTTP session and release its resources."""
        self.session.close()


def is_google_redirect(url: str | None) -> bool:
    if not url:
        return False

    parsed = urlparse(url)

    return (
        parsed.hostname in {
            "www.google.com",
            "google.com",
            "www.google.co",
            "google.co",
        }
        and parsed.path == "/goto"
    )
