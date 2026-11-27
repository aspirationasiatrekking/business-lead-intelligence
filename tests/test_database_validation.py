import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    PersistenceError,
    PersistenceValidationError,
    RecordNotFoundError,
)
from src.lead_intelligence.database.models.common import (
    MAX_BUSINESS_CITY_BYTES,
    MAX_NORMALIZED_ADDRESS_BYTES,
    MAX_NORMALIZED_CONTACT_BYTES,
    MAX_NORMALIZED_NAME_BYTES,
    MAX_SOURCE_URL_BYTES,
    MAX_WEBSITE_DOMAIN_BYTES,
)
from src.lead_intelligence.database.validation import (
    validate_business_city,
    validate_normalized_address,
    validate_normalized_contact,
    validate_normalized_name,
    validate_search_signature,
    validate_source_url,
    validate_text,
    validate_website_domain,
)
from src.lead_intelligence.models.search_request import SearchRequest


@pytest.mark.parametrize(
    "exception",
    [
        PersistenceValidationError,
        RecordNotFoundError,
        PersistenceConflictError,
    ],
)
def test_persistence_exception_hierarchy(exception):
    assert issubclass(exception, PersistenceError)


@pytest.mark.parametrize(
    "value",
    [
        "Kathmandu",
        "  Preserved whitespace  ",
        "काठमाडौं",
        "東京",
        "München",
    ],
)
def test_validate_text_preserves_valid_values(value):
    assert (
        validate_text(
            value,
            field_name="Test field",
        )
        == value
    )


@pytest.mark.parametrize(
    "value",
    [None, 123, True, [], {}],
)
def test_validate_text_rejects_invalid_types(value):
    with pytest.raises(PersistenceValidationError):
        validate_text(
            value,
            field_name="Test field",
        )


@pytest.mark.parametrize(
    "value",
    ["", " ", "\t", "\n", " \t\n "],
)
def test_validate_text_rejects_blank_values(value):
    with pytest.raises(
        PersistenceValidationError,
        match="must not be empty",
    ):
        validate_text(
            value,
            field_name="Test field",
        )


def test_validate_text_accepts_nullable_none():
    assert (
        validate_text(
            None,
            field_name="Optional field",
            nullable=True,
        )
        is None
    )


def test_validate_text_allows_blank_when_requested():
    assert (
        validate_text(
            "",
            field_name="Optional text",
            allow_blank=True,
        )
        == ""
    )


@pytest.mark.parametrize(
    "value",
    ["\x00", "Business\x00Name"],
)
def test_validate_text_rejects_null_characters(value):
    with pytest.raises(
        PersistenceValidationError,
        match="null character",
    ):
        validate_text(
            value,
            field_name="Test field",
        )


def test_validate_text_rejects_invalid_unicode():
    with pytest.raises(
        PersistenceValidationError,
        match="invalid Unicode",
    ):
        validate_text(
            "\ud800",
            field_name="Test field",
        )


def test_validate_text_accepts_exact_byte_limit():
    value = "a" * 512

    assert (
        validate_text(
            value,
            field_name="Test field",
            max_bytes=512,
        )
        == value
    )


def test_validate_text_rejects_excess_bytes():
    with pytest.raises(
        PersistenceValidationError,
        match="exceeds 512 UTF-8 bytes",
    ):
        validate_text(
            "a" * 513,
            field_name="Test field",
            max_bytes=512,
        )


def test_validate_text_accepts_unicode_at_byte_limit():
    value = "é" * 256

    assert len(value.encode("utf-8")) == 512

    assert (
        validate_text(
            value,
            field_name="Test field",
            max_bytes=512,
        )
        == value
    )


def test_validate_text_rejects_unicode_over_byte_limit():
    value = "é" * 257

    assert len(value) == 257
    assert len(value.encode("utf-8")) == 514

    with pytest.raises(PersistenceValidationError):
        validate_text(
            value,
            field_name="Test field",
            max_bytes=512,
        )


INDEXED_VALIDATORS = (
    (
        validate_normalized_name,
        MAX_NORMALIZED_NAME_BYTES,
    ),
    (
        validate_normalized_address,
        MAX_NORMALIZED_ADDRESS_BYTES,
    ),
    (
        validate_website_domain,
        MAX_WEBSITE_DOMAIN_BYTES,
    ),
    (
        validate_business_city,
        MAX_BUSINESS_CITY_BYTES,
    ),
    (
        validate_normalized_contact,
        MAX_NORMALIZED_CONTACT_BYTES,
    ),
    (
        validate_source_url,
        MAX_SOURCE_URL_BYTES,
    ),
)


@pytest.mark.parametrize(
    ("validator", "limit"),
    INDEXED_VALIDATORS,
)
def test_indexed_validators_accept_exact_limit(
    validator,
    limit,
):
    value = "a" * limit

    assert validator(value) == value


@pytest.mark.parametrize(
    ("validator", "limit"),
    INDEXED_VALIDATORS,
)
def test_indexed_validators_reject_excess_bytes(
    validator,
    limit,
):
    with pytest.raises(PersistenceValidationError):
        validator("a" * (limit + 1))


@pytest.mark.parametrize(
    "validator",
    [
        validate_normalized_address,
        validate_website_domain,
        validate_business_city,
    ],
)
def test_optional_validators_accept_none(validator):
    assert validator(None) is None


@pytest.mark.parametrize(
    "validator",
    [
        validate_normalized_name,
        validate_normalized_contact,
        validate_source_url,
    ],
)
def test_required_validators_reject_none(validator):
    with pytest.raises(PersistenceValidationError):
        validator(None)


def test_validation_error_does_not_expose_input():
    sensitive_value = "private-test-value" * 100

    with pytest.raises(
        PersistenceValidationError,
    ) as captured:
        validate_normalized_name(sensitive_value)

    assert sensitive_value not in str(captured.value)


def test_validate_search_signature():
    request = SearchRequest(
        country_code="NP",
        city="Kathmandu",
        query="Trekking Agencies",
    )

    assert validate_search_signature(request) == (
        "NP",
        "kathmandu",
        "trekking agencies",
    )


def test_validate_search_signature_preserves_unicode():
    request = SearchRequest(
        country_code="NP",
        city="काठमाडौं",
        query="यात्रा कम्पनी",
    )

    assert validate_search_signature(request) == request.signature


@pytest.mark.parametrize(
    "request_value",
    [None, {}, "Trekking companies"],
)
def test_validate_search_signature_rejects_invalid_request(
    request_value,
):
    with pytest.raises(
        PersistenceValidationError,
        match="SearchRequest",
    ):
        validate_search_signature(request_value)


def test_validate_search_signature_rejects_excess_bytes(
    monkeypatch,
):
    request = SearchRequest(
        country_code="NP",
        city="Kathmandu",
        query="Trekking",
    )

    monkeypatch.setattr(
        "src.lead_intelligence.database.validation.MAX_SEARCH_SIGNATURE_BYTES",
        5,
    )

    with pytest.raises(
        PersistenceValidationError,
        match="Normalized search signature exceeds",
    ):
        validate_search_signature(request)


def test_validate_search_signature_accepts_exact_budget(
    monkeypatch,
):
    request = SearchRequest(
        country_code="NP",
        city="Kathmandu",
        query="Trekking",
    )

    _, city, query = request.signature

    byte_count = len(city.encode("utf-8")) + len(query.encode("utf-8"))

    monkeypatch.setattr(
        "src.lead_intelligence.database.validation.MAX_SEARCH_SIGNATURE_BYTES",
        byte_count,
    )

    assert validate_search_signature(request) == request.signature
