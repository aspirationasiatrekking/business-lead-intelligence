import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
from requests_ratelimiter import LimiterSession
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.lead_intelligence.settings import ApplicationSettings
from src.lead_intelligence.utils.country_utils import (
    normalize_country_code,
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 30.0


class SerperResponseError(ValueError):
    """Raised when Serper returns an unexpected response structure."""


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

        return response is not None and response.status_code in RETRYABLE_STATUS_CODES

    return False


def get_retry_after_seconds(error: Exception) -> float | None:
    """Extract a finite Retry-After delay from an HTTP response."""
    if not isinstance(error, requests.exceptions.HTTPError):
        return None

    response = error.response

    if response is None or response.status_code != 429:
        return None

    retry_after = response.headers.get("Retry-After")

    if not isinstance(retry_after, str):
        return None

    retry_after = retry_after.strip()

    if not retry_after:
        return None

    # Handle numeric delays.
    try:
        delay = float(retry_after)

        if not math.isfinite(delay):
            return None

        return max(0.0, delay)

    except ValueError:
        pass

    # Handle HTTP date delays.
    try:
        retry_date = parsedate_to_datetime(retry_after)

        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=UTC)

        delay = (retry_date - datetime.now(UTC)).total_seconds()

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

    def __init__(self, settings: ApplicationSettings | None = None):
        self.settings = settings if settings is not None else ApplicationSettings.load()
        self.api_key = self.settings.serper_api_key

        if not self.api_key:
            raise ValueError("SERPER_API_KEY is missing from configuration")

        self.session = LimiterSession(
            per_second=self.settings.serper_rps,
            burst=1,
            max_delay=30,
        )
        self.session.trust_env = False

    @staticmethod
    def _validate_places_response(data: dict) -> dict:
        """Validate the structure of a Serper Places API response."""

        if not isinstance(data, dict):
            raise SerperResponseError("Serper Places response must be a dictionary.")

        if "places" not in data:
            raise SerperResponseError(
                "Serper Places response is missing the 'places' field."
            )

        if not isinstance(data["places"], list):
            raise SerperResponseError(
                "Serper Places response field 'places' must be a list."
            )

        return data

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
            timeout=self.settings.serper_timeout,
            allow_redirects=False,
        )

        if 300 <= response.status_code < 400:
            response.close()
            raise SerperResponseError("Unexpected Serper redirect response")

        response.raise_for_status()

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise SerperResponseError("Serper API returned invalid JSON.") from exc

    def search_places(
        self,
        query: str,
        country: str | None = None,
        page: int = 1,
        num: int = 10,
    ) -> dict:
        if not isinstance(query, str):
            raise TypeError("Search query must be a string")

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        country = normalize_country_code(country)

        if not isinstance(page, int) or isinstance(page, bool):
            raise TypeError("Page must be an integer")

        if page < 1:
            raise ValueError("Page must be greater than or equal to 1")

        if not isinstance(num, int) or isinstance(num, bool):
            raise TypeError("Number of results must be an integer")

        if not 1 <= num <= 100:
            raise ValueError("Number of results must be between 1 and 100")

        payload = {
            "q": query,
            "hl": "en",
            "page": page,
            "num": num,
        }

        if country is not None:
            payload["gl"] = country

        response = self._post("places", payload)

        return self._validate_places_response(response)

    def resolve_links(self, results: dict) -> dict:
        """Resolve supported Google redirects in Serper Places results."""
        self._validate_places_response(results)

        places = results["places"]

        if not places:
            return results

        # Preserve malformed records for downstream failure reporting.
        if any(not isinstance(place, dict) for place in places):
            return results

        has_redirects = any(
            is_google_redirect(place.get("website")) for place in places
        )

        if not has_redirects:
            return results

        response = self._post("resolve", results)

        return self._validate_places_response(response)

    def close(self):
        """Close the HTTP session and release its resources."""
        self.session.close()


def is_google_redirect(url: str | None) -> bool:
    """Identify supported Google business website redirect URLs."""
    if not isinstance(url, str):
        return False

    url = url.strip()

    if not url:
        return False

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        # Accessing port also validates malformed port values.
        _ = parsed.port

    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    if parsed.username is not None or parsed.password is not None:
        return False

    return (
        hostname
        in {
            "www.google.com",
            "google.com",
            "www.google.co",
            "google.co",
        }
        and parsed.path == "/goto"
    )
