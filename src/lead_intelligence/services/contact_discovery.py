from src.lead_intelligence.extractors.contact_extractor import (
    extract_emails,
    extract_phone_numbers,
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.scrapers.website_scraper import (
    extract_website_text,
    fetch_website,
    fetch_website_html,
    find_contact_pages,
)
from src.lead_intelligence.utils.country_utils import normalize_country_code
from src.lead_intelligence.utils.url_utils import is_valid_website


class ContactDiscoveryService:
    MAX_CONTACT_PAGES = 5

    @staticmethod
    def _extract_contacts(
        text: str,
        region: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Extract validated email addresses and phone numbers."""
        return (
            extract_emails(text),
            extract_phone_numbers(text, region=region),
        )

    def discover(
        self,
        business: Business,
        region: str | None = None,
    ) -> Business:
        """Discover website contacts and update extraction metadata."""
        normalized_region = normalize_country_code(region)

        if normalized_region is not None:
            normalized_region = normalized_region.upper()

        # Track the contacts before discovery for score invalidation.
        original_emails = business.emails.copy()
        original_phones = business.phone_numbers.copy()

        # Extraction status and discovered pages describe this attempt.
        business.extraction_status = ExtractionStatus.PENDING
        business.contact_page_urls = []

        if not business.website or not is_valid_website(business.website):
            business.extraction_status = ExtractionStatus.NO_WEBSITE
            return business

        homepage_url = business.website

        # Fetch the homepage only once.
        homepage_html = fetch_website_html(homepage_url)

        if homepage_html is None:
            business.extraction_status = ExtractionStatus.FAILED
            return business

        website_emails = []
        website_phones = []

        # Preserve previously recorded contributing sources.
        source_urls = business.source_urls.copy()

        had_failures = False

        # Extract homepage contacts.
        homepage_text = extract_website_text(homepage_html)

        emails, phones = self._extract_contacts(
            homepage_text,
            region=normalized_region,
        )

        website_emails.extend(emails)
        website_phones.extend(phones)

        if emails or phones:
            source_urls.append(homepage_url)

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

        for page_url in pages_to_fetch:
            page_text = fetch_website(page_url)

            # None represents a fetch failure.
            # Empty text represents a successfully fetched empty page.
            if page_text is None:
                had_failures = True
                continue

            emails, phones = self._extract_contacts(
                page_text,
                region=normalized_region,
            )

            website_emails.extend(emails)
            website_phones.extend(phones)

            # Only record pages that contributed contact information.
            if emails or phones:
                source_urls.append(page_url)

        # Merge existing and newly extracted email addresses.
        business.emails = list(dict.fromkeys(business.emails + website_emails))

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
            business.lead_score = None

        # Determine the final extraction status.
        if had_failures:
            business.extraction_status = ExtractionStatus.PARTIAL

        elif website_emails or website_phones:
            business.extraction_status = ExtractionStatus.SUCCESS

        else:
            business.extraction_status = ExtractionStatus.NO_CONTACTS

        return business
