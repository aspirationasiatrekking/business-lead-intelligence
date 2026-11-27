from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.models import BusinessSourceRecord
from src.lead_intelligence.database.validation import (
    validate_source_url,
)
from src.lead_intelligence.models.business import Business


def business_to_source_records(
    business: Business,
) -> list[BusinessSourceRecord]:
    """Map discovery, website and contact page evidence."""

    if not isinstance(business, Business):
        raise PersistenceValidationError("A valid Business instance is required.")

    if not isinstance(business.source_urls, list):
        raise PersistenceValidationError("Business source URLs must be a list.")

    if not isinstance(business.contact_page_urls, list):
        raise PersistenceValidationError("Contact page URLs must be a list.")

    records: list[BusinessSourceRecord] = []
    seen: set[tuple[str, str]] = set()

    website_urls = [business.website] if business.website is not None else []

    groups = (
        ("discovery", business.source_urls),
        ("website", website_urls),
        ("contact_page", business.contact_page_urls),
    )

    for source_type, urls in groups:
        for url in urls:
            validate_source_url(url)

            identity = (source_type, url)

            if identity in seen:
                continue

            records.append(
                BusinessSourceRecord(
                    source_type=source_type,
                    source_url=url,
                    verification_status="unknown",
                )
            )

            seen.add(identity)

    return records
