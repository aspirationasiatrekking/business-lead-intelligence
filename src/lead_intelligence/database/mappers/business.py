from copy import deepcopy

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.contacts import (
    business_to_contact_records,
)
from src.lead_intelligence.database.mappers.sources import (
    business_to_source_records,
)
from src.lead_intelligence.database.models import BusinessRecord
from src.lead_intelligence.database.validation import (
    validate_business_city,
    validate_normalized_address,
    validate_normalized_name,
    validate_text,
    validate_website_domain,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.services.lead_scoring import (
    LeadScoringService,
)


def validate_geographic_metadata(
    business: Business,
) -> None:
    """Validate text contained in geographic JSON metadata."""

    for key, sources in business.geographic_sources.items():
        validate_text(
            key,
            field_name="Geographic source key",
        )

        for source in sources:
            validate_text(
                source,
                field_name="Geographic source",
            )

    for conflict in business.geographic_conflicts:
        validate_text(
            conflict,
            field_name="Geographic conflict",
        )


def business_to_record(
    business: Business,
) -> BusinessRecord:
    """Convert a domain business into a new ORM business record."""

    if not isinstance(business, Business):
        raise PersistenceValidationError("A valid Business instance is required.")

    # The domain model is mutable, so validate a separate copy
    # before constructing the database record.
    business = deepcopy(business)

    try:
        business.__post_init__()

    except (TypeError, ValueError):
        raise PersistenceValidationError(
            "Business contains invalid domain data."
        ) from None

    validate_text(
        business.name,
        field_name="Business name",
    )

    optional_fields = (
        "address",
        "website",
        "category",
        "district",
        "state",
        "country",
        "country_code",
        "serper_cid",
        "score_version",
        "website_source",
    )

    for field_name in optional_fields:
        validate_text(
            getattr(business, field_name),
            field_name=field_name,
            nullable=True,
        )

    validate_text(
        business.website_status,
        field_name="Website status",
    )

    validate_geographic_metadata(business)

    name_normalized = validate_normalized_name(
        BusinessDeduplicationService.normalize_text(
            business.name,
        )
    )

    address_normalized = validate_normalized_address(
        BusinessDeduplicationService.normalize_text(
            business.address,
        )
        or None
    )

    website_domain = validate_website_domain(
        BusinessDeduplicationService.normalize_domain(
            business.website,
        )
    )

    city = validate_business_city(business.city)

    return BusinessRecord(
        name=business.name,
        name_normalized=name_normalized,
        address=business.address,
        address_normalized=address_normalized,
        website=business.website,
        website_domain=website_domain,
        category=business.category,
        city=city,
        district=business.district,
        state=business.state,
        country=business.country,
        country_code=business.country_code,
        serper_cid=business.serper_cid,
        latitude=business.latitude,
        longitude=business.longitude,
        extraction_status=business.extraction_status.value,
        website_status=business.website_status,
        website_source=business.website_source,
        geographic_sources=deepcopy(
            business.geographic_sources,
        ),
        geographic_conflicts=business.geographic_conflicts.copy(),
        lead_score=business.lead_score,
        score_version=business.score_version,
    )


def record_to_business(
    record: BusinessRecord,
) -> Business:
    """Reconstruct scalar business information from an ORM record.

    Contact and source relationships are mapped separately.
    """

    if not isinstance(record, BusinessRecord):
        raise PersistenceValidationError("A valid BusinessRecord instance is required.")

    return Business(
        name=record.name,
        address=record.address,
        website=record.website,
        category=record.category,
        city=record.city,
        district=record.district,
        state=record.state,
        country=record.country,
        country_code=record.country_code,
        serper_cid=record.serper_cid,
        latitude=record.latitude,
        longitude=record.longitude,
        extraction_status=ExtractionStatus(
            record.extraction_status,
        ),
        website_status=record.website_status,
        website_source=record.website_source,
        geographic_sources=deepcopy(
            record.geographic_sources,
        ),
        geographic_conflicts=record.geographic_conflicts.copy(),
        # Scalar reconstruction does not restore scoring inputs
        # such as contacts. Recalculate after full hydration.
        lead_score=None,
        score_version=None,
    )


def business_to_complete_record(
    business: Business,
    *,
    region: str | None = None,
) -> BusinessRecord:
    """Map a complete domain business and its relationships."""

    record = business_to_record(business)

    prepared = deepcopy(business)
    prepared.__post_init__()

    record.contacts = business_to_contact_records(
        prepared,
        region=region,
    )
    record.sources = business_to_source_records(prepared)

    # Recalculate the score using the actual persisted representation.
    restored = complete_record_to_business(
        record,
        region=region,
    )

    record.lead_score = restored.lead_score
    record.score_version = restored.score_version

    return record


def complete_record_to_business(
    record: BusinessRecord,
    *,
    region: str | None = None,
) -> Business:
    """Reconstruct a complete business from loaded ORM relationships."""

    business = record_to_business(record)

    for contact in record.contacts:
        normalized = contact.normalized_value

        urls = list(dict.fromkeys(source.source_url for source in contact.sources))

        if contact.contact_type == "email":
            business.emails.append(normalized)

            if urls:
                business.email_sources[normalized] = urls

        elif contact.contact_type == "phone":
            business.phone_numbers.append(normalized)

            if urls:
                business.phone_sources[normalized] = urls

        else:
            raise PersistenceValidationError("Stored contact has an unsupported type.")

    for source in record.sources:
        if source.source_type == "discovery":
            business.source_urls.append(
                source.source_url,
            )

        elif source.source_type == "contact_page":
            business.contact_page_urls.append(
                source.source_url,
            )

        elif source.source_type == "website":
            # The canonical website comes from BusinessRecord.
            continue

        else:
            raise PersistenceValidationError(
                "Stored business source has an unsupported type."
            )

    business.emails = list(dict.fromkeys(business.emails))

    business.phone_numbers = list(dict.fromkeys(business.phone_numbers))

    business.source_urls = list(dict.fromkeys(business.source_urls))

    business.contact_page_urls = list(dict.fromkeys(business.contact_page_urls))

    LeadScoringService().evaluate_business(
        business,
        region=region,
    )

    return business
