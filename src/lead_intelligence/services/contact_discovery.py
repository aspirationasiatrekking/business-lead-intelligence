from src.lead_intelligence.extractors.contact_extractor import (
    extract_emails,
    extract_phone_numbers,
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.scrapers.website_scraper import (
    extract_website_text,
    fetch_website,
    fetch_website_html,
    find_contact_pages,
)


class ContactDiscoveryService:
    def discover(self, business: Business, region: str | None = None) -> Business:

        if not business.website:
            return business

        # Fetch homepage HTML once
        homepage_html = fetch_website_html(business.website)

        if homepage_html is None:
            return business

        # Extract homepage text
        website_texts = [extract_website_text(homepage_html)]

        # Discover contact page URLs using existing homepage HTML
        contact_pages = find_contact_pages(business.website, homepage_html)[:5]

        # Fetch and extract contact pages
        for page_url in contact_pages:
            page_text = fetch_website(page_url)

            if page_text:
                website_texts.append(page_text)

        # Extract emails and phone numbers from all pages
        emails = []
        phone_numbers = []

        for text in website_texts:
            emails.extend(extract_emails(text))

            phone_numbers.extend(extract_phone_numbers(text, region=region))

        # Merge and deduplicate emails
        business.emails = list(dict.fromkeys(business.emails + emails))

        # Normalize and deduplicate phone numbers
        normalized_numbers = [
            normalize_phone_number(number, region=region)
            for number in business.phone_numbers + phone_numbers
        ]

        business.phone_numbers = list(
            dict.fromkeys(number for number in normalized_numbers if number)
        )

        return business
