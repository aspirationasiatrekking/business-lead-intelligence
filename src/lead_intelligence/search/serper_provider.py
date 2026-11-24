
import os
from urllib.parse import urlparse   
import requests
from dotenv import load_dotenv
from xlsxwriter import url


load_dotenv()


class SerperSearchProvider:

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise ValueError("SERPER_API_KEY is missing from .env")

    def search_places(
        self,
        query: str,
        country: str | None = None,
        language: str = "en",
        page: int = 1
    ):
        url = "https://google.serper.dev/places"

        payload = {
            "q": query,
            "gl": country
        }

        if country:
            payload["gl"] = country

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    
    def resolve_links(self, results: dict) -> dict:
        url = "https://google.serper.dev/resolve"

        headers = {
        "X-API-KEY": self.api_key,
        "Content-Type": "application/json"
        }

        response = requests.post(
        url,
        json=results,
        headers=headers,
        timeout=30
        )

        response.raise_for_status()

        return response.json()




def is_google_redirect(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return (
        parsed.hostname in {
            "www.google.com", "google.com", "www.google.co", "google.co"
            }
            and parsed.path == "/goto"
        )


    
