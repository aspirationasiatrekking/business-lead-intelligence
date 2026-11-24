
import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


load_dotenv()


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


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


class SerperSearchProvider:

    BASE_URL = "https://google.serper.dev"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise ValueError("SERPER_API_KEY is missing from .env")

    @retry(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _post(self, endpoint: str, payload: dict) -> dict:
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        response = requests.post(
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
        language: str = "en",
        page: int = 1,
    ) -> dict:

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if page < 1:
            raise ValueError("Page must be greater than or equal to 1")

        payload = {
            "q": query.strip(),
            "hl": language,
            "page": page,
        }

        if country:
            payload["gl"] = country

        return self._post("places", payload)

    def resolve_links(self, results: dict) -> dict:
        return self._post("resolve", results)


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
