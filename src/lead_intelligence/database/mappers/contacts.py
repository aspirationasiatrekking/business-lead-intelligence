from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    ContactSourceRecord,
)
from src.lead_intelligence.database.validation import (
    validate_normalized_contact,
    validate_source_url,
    validate_text,
)
from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business


def normalize_contact_value(
    contact_type: str,
    value: str,
    region: str | None = None,
) -> str:
    """Build a contact identity without discarding unrecognized values."""

    validate_text(
        value,
        field_name="Contact value",
    )

    value = value.strip()

    if contact_type == "email":
        normalized = value.lower()

    elif contact_type == "phone":
        normalized = (
            normalize_phone_number(
                value,
                region=region,
            )
            or value
        )

    else:
        raise PersistenceValidationError("Unsupported contact type.")

    return validate_normalized_contact(normalized)


def build_contact_records(
    contact_type: str,
    values: list[str],
    evidence: dict[str, list[str]],
    region: str | None = None,
) -> list[BusinessContactRecord]:
    """Convert contacts and their evidence into unique ORM records."""

    if contact_type not in {"email", "phone"}:
        raise PersistenceValidationError("Unsupported contact type.")

    if not isinstance(values, list):
        raise PersistenceValidationError("Contact values must be a list.")

    if not isinstance(evidence, dict):
        raise PersistenceValidationError("Contact evidence must be a dictionary.")

    records: dict[str, BusinessContactRecord] = {}

    for value in values:
        normalized = normalize_contact_value(
            contact_type,
            value,
            region,
        )

        if normalized not in records:
            records[normalized] = BusinessContactRecord(
                contact_type=contact_type,
                value=value.strip(),
                normalized_value=normalized,
                sources=[],
            )

    seen_sources: dict[str, set[str]] = {key: set() for key in records}

    for key, urls in evidence.items():
        normalized = normalize_contact_value(
            contact_type,
            key,
            region,
        )

        if normalized not in records:
            raise PersistenceValidationError(
                "Contact evidence has no matching contact."
            )

        if not isinstance(urls, list):
            raise PersistenceValidationError("Contact source URLs must be a list.")

        record = records[normalized]

        for url in urls:
            validate_source_url(url)

            if url in seen_sources[normalized]:
                continue

            record.sources.append(
                ContactSourceRecord(
                    source_url=url,
                )
            )

            seen_sources[normalized].add(url)

    return list(records.values())


def business_to_contact_records(
    business: Business,
    *,
    region: str | None = None,
) -> list[BusinessContactRecord]:
    """Map all contacts belonging to a domain business."""

    if not isinstance(business, Business):
        raise PersistenceValidationError("A valid Business instance is required.")

    selected_region = business.country_code or region

    email_records = build_contact_records(
        contact_type="email",
        values=business.emails,
        evidence=business.email_sources,
    )

    phone_records = build_contact_records(
        contact_type="phone",
        values=business.phone_numbers,
        evidence=business.phone_sources,
        region=selected_region,
    )

    return email_records + phone_records
