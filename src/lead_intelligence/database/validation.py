from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.models.common import (
    MAX_BUSINESS_CITY_BYTES,
    MAX_NORMALIZED_ADDRESS_BYTES,
    MAX_NORMALIZED_CONTACT_BYTES,
    MAX_NORMALIZED_NAME_BYTES,
    MAX_SEARCH_SIGNATURE_BYTES,
    MAX_SOURCE_URL_BYTES,
    MAX_WEBSITE_DOMAIN_BYTES,
)
from src.lead_intelligence.models.search_request import SearchRequest


def validate_text(
    value: str | None,
    *,
    field_name: str,
    max_bytes: int | None = None,
    nullable: bool = False,
    allow_blank: bool = False,
) -> str | None:
    """Validate PostgreSQL-compatible text without truncating it."""

    if value is None:
        if nullable:
            return None

        raise PersistenceValidationError(f"{field_name} is required.")

    if not isinstance(value, str):
        raise PersistenceValidationError(f"{field_name} must be a string.")

    if "\x00" in value:
        raise PersistenceValidationError(f"{field_name} contains a null character.")

    if not allow_blank and not value.strip():
        raise PersistenceValidationError(f"{field_name} must not be empty.")

    try:
        encoded = value.encode("utf-8")

    except UnicodeEncodeError:
        raise PersistenceValidationError(
            f"{field_name} contains invalid Unicode."
        ) from None

    if max_bytes is not None and len(encoded) > max_bytes:
        raise PersistenceValidationError(
            f"{field_name} exceeds {max_bytes} UTF-8 bytes."
        )

    return value


def validate_normalized_name(value: str) -> str:
    """Validate an indexed normalized business name."""

    return validate_text(
        value,
        field_name="Normalized business name",
        max_bytes=MAX_NORMALIZED_NAME_BYTES,
    )


def validate_normalized_address(
    value: str | None,
) -> str | None:
    """Validate an optional indexed business address."""

    return validate_text(
        value,
        field_name="Normalized business address",
        max_bytes=MAX_NORMALIZED_ADDRESS_BYTES,
        nullable=True,
    )


def validate_website_domain(
    value: str | None,
) -> str | None:
    """Validate an optional indexed website domain."""

    return validate_text(
        value,
        field_name="Website domain",
        max_bytes=MAX_WEBSITE_DOMAIN_BYTES,
        nullable=True,
    )


def validate_business_city(
    value: str | None,
) -> str | None:
    """Validate an optional indexed business city."""

    return validate_text(
        value,
        field_name="Business city",
        max_bytes=MAX_BUSINESS_CITY_BYTES,
        nullable=True,
    )


def validate_normalized_contact(value: str) -> str:
    """Validate an indexed contact identity."""

    return validate_text(
        value,
        field_name="Normalized contact",
        max_bytes=MAX_NORMALIZED_CONTACT_BYTES,
    )


def validate_source_url(value: str) -> str:
    """Validate the storage representation of a source URL."""

    return validate_text(
        value,
        field_name="Source URL",
        max_bytes=MAX_SOURCE_URL_BYTES,
    )


def validate_search_signature(
    request: SearchRequest,
) -> tuple[str, str, str]:
    """Validate a normalized search signature before storage."""

    if not isinstance(request, SearchRequest):
        raise PersistenceValidationError("A valid SearchRequest is required.")

    country_code, city, query = request.signature

    validate_text(
        city,
        field_name="Normalized search city",
    )

    validate_text(
        query,
        field_name="Normalized search query",
    )

    combined_bytes = len(city.encode("utf-8")) + len(query.encode("utf-8"))

    if combined_bytes > MAX_SEARCH_SIGNATURE_BYTES:
        raise PersistenceValidationError(
            "Normalized search signature exceeds "
            f"{MAX_SEARCH_SIGNATURE_BYTES} UTF-8 bytes."
        )

    return country_code, city, query
