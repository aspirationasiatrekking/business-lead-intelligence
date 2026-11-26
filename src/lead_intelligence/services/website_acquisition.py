"""Conservative candidate verification using name and existing business phone."""

import re
from collections import Counter
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.lead_intelligence.extractors.contact_extractor import extract_html_contacts
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.scrapers.website_scraper import fetch_website_page
from src.lead_intelligence.utils.url_utils import normalize_website_url
from src.lead_intelligence.utils.website_policy import (
    is_candidate_business_website,
    same_website,
)


def name_key(value: str) -> str:
    words = re.findall(r"[^\W_]+", value.casefold())
    while words and words[-1] in {"ltd", "limited", "llc", "inc", "pvt"}:
        words.pop()
    return " ".join(words)


class WebsiteAcquisitionService:
    def __init__(self) -> None:
        self.candidate_outcomes: Counter[str] = Counter()

    def acquire(self, business: Business, response: dict, region=None) -> bool:
        self.candidate_outcomes.clear()
        if business.website or not business.phone_numbers:
            return False
        name = name_key(business.name)
        if len(name.split()) < 2:
            return False
        candidates = response.get("organic", [])
        if not isinstance(candidates, list):
            return False
        checked = set()
        matches = []
        for item in candidates[:5]:
            if not isinstance(item, dict):
                self.candidate_outcomes["malformed"] += 1
                continue
            url = item.get("link")
            if not is_candidate_business_website(url):
                self.candidate_outcomes["rejected_url"] += 1
                continue
            parsed = urlparse(url)
            # Verify the site's homepage, not an article about the business.
            candidate = normalize_website_url(f"{parsed.scheme}://{parsed.netloc}")
            if not candidate or candidate in checked:
                self.candidate_outcomes["duplicate_or_invalid"] += 1
                continue
            checked.add(candidate)
            page = fetch_website_page(candidate, business_only=True)
            if page is None or not same_website(candidate, page.final_url):
                self.candidate_outcomes["fetch_or_site_failure"] += 1
                continue
            soup = BeautifulSoup(page.html, "html.parser")
            labels = [
                tag.get_text(" ", strip=True) for tag in soup.find_all(["title", "h1"])
            ]
            if not any(f" {name} " in f" {name_key(label)} " for label in labels):
                self.candidate_outcomes["name_mismatch"] += 1
                continue
            _, phones = extract_html_contacts(
                page.html, region=business.country_code or region
            )
            if not set(phones).intersection(business.phone_numbers):
                self.candidate_outcomes["phone_mismatch"] += 1
                continue
            self.candidate_outcomes["matched"] += 1
            if not any(same_website(existing, page.final_url) for existing in matches):
                matches.append(page.final_url)
        if len(matches) != 1:
            business.website_status = "ambiguous" if matches else "unverified"
            return False
        business.website = normalize_website_url(matches[0])
        business.website_status = "accepted"
        business.website_source = "organic_name_phone"
        business.invalidate_score()
        return True
