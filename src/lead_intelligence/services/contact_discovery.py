from src.lead_intelligence.extractors.contact_extractor import (
    extract_html_contacts,
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.scrapers.website_scraper import (
    fetch_website_page,
    find_contact_pages,
    normalize_page_url,
)
from src.lead_intelligence.utils.country_utils import normalize_country_code
from src.lead_intelligence.utils.website_policy import (
    is_candidate_business_website,
    same_website,
)


# Separate entry points keep homepage and contact-page tests isolated.
def fetch_homepage(url: str):
    return fetch_website_page(url, business_only=True)


def fetch_contact_page(url: str):
    return fetch_website_page(url, business_only=True)


class ContactDiscoveryService:
    MAX_CONTACT_PAGES = 5

    @staticmethod
    def _extract_contacts(
        text: str,
        region: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Extract validated email addresses and phone numbers."""
        return extract_html_contacts(text, region=region)

    @staticmethod
    def _record_sources(
        business: Business, emails: list[str], phones: list[str], url: str
    ) -> None:
        for values, mapping in (
            (emails, business.email_sources),
            (phones, business.phone_sources),
        ):
            for value in values:
                urls = mapping.setdefault(value.casefold(), [])
                if url not in urls:
                    urls.append(url)

    def discover(
        self,
        business: Business,
        region: str | None = None,
    ) -> Business:
        """Discover website contacts and update extraction metadata."""
        normalized_region = normalize_country_code(region)

        if normalized_region is not None:
            normalized_region = normalized_region.upper()

        if business.country_code is not None:
            normalized_region = business.country_code

        # Track the contacts before discovery for score invalidation.
        original_emails = business.emails.copy()
        original_phones = business.phone_numbers.copy()

        # Extraction status and discovered pages describe this attempt.
        business.extraction_status = ExtractionStatus.PENDING
        business.contact_page_urls = []

        if not business.website or not is_candidate_business_website(business.website):
            business.extraction_status = ExtractionStatus.NO_WEBSITE
            return business

        homepage_url = business.website

        # Fetch the homepage only once.
        homepage = fetch_homepage(homepage_url)

        if homepage is None or not same_website(homepage_url, homepage.final_url):
            business.extraction_status = ExtractionStatus.FAILED
            return business

        homepage_url = homepage.final_url
        homepage_html = homepage.html

        website_emails = []
        website_phones = []

        # Preserve previously recorded contributing sources.
        source_urls = business.source_urls.copy()

        had_failures = False

        # Extract homepage contacts.
        emails, phones = self._extract_contacts(
            homepage_html,
            region=normalized_region,
        )

        website_emails.extend(emails)
        website_phones.extend(phones)

        if emails or phones:
            source_urls.append(homepage_url)
            self._record_sources(business, emails, phones, homepage_url)

        # Discover contact-related pages using existing homepage HTML.
        try:
            discovered_pages = find_contact_pages(
                homepage_url,
                homepage_html,
            )
        except ValueError:
            discovered_pages = []
            had_failures = True

        # Preserve unique discovered contact page URLs.
        business.contact_page_urls = list(dict.fromkeys(discovered_pages))

        # Limit the number of contact pages actually fetched.
        pages_to_fetch = business.contact_page_urls[: self.MAX_CONTACT_PAGES]

        visited = {normalize_page_url(homepage_url)}
        for page_url in pages_to_fetch:
            if not same_website(homepage_url, page_url):
                had_failures = True
                continue
            if normalize_page_url(page_url) in visited:
                continue
            visited.add(normalize_page_url(page_url))
            page = fetch_contact_page(page_url)

            # None represents a fetch failure.
            # Empty text represents a successfully fetched empty page.
            if page is None or not same_website(homepage_url, page.final_url):
                had_failures = True
                continue

            final_key = normalize_page_url(page.final_url)
            if final_key != normalize_page_url(page_url) and final_key in visited:
                continue
            visited.add(final_key)
            emails, phones = self._extract_contacts(
                page.html,
                region=normalized_region,
            )

            website_emails.extend(emails)
            website_phones.extend(phones)

            # Only record pages that contributed contact information.
            if emails or phones:
                source_urls.append(page.final_url)
                self._record_sources(business, emails, phones, page.final_url)

        # Merge existing and newly extracted email addresses.
        unique_emails = {}
        for email in business.emails + website_emails:
            if email.strip():
                unique_emails.setdefault(email.strip().casefold(), email.strip())
        business.emails = list(unique_emails.values())

        # Normalize and deduplicate existing and extracted phones.
        normalized_numbers = [
            normalize_phone_number(
                number,
                region=normalized_region,
            )
            for number in business.phone_numbers + website_phones
        ]

        business.phone_numbers = list(
            dict.fromkeys(number for number in normalized_numbers if number)
        )

        business.source_urls = list(dict.fromkeys(source_urls))

        # Invalidate previously calculated scores if contacts changed.
        if (
            business.emails != original_emails
            or business.phone_numbers != original_phones
        ):
            business.invalidate_score()

        # Determine the final extraction status.
        if had_failures:
            business.extraction_status = ExtractionStatus.PARTIAL

        elif website_emails or website_phones:
            business.extraction_status = ExtractionStatus.SUCCESS

        else:
            business.extraction_status = ExtractionStatus.NO_CONTACTS

        return business
