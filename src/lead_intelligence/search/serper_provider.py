
import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


load_dotenv()


class SerperSearchProvider:

    BASE_URL = "https://google.serper.dev"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise ValueError("SERPER_API_KEY is missing from .env")

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
