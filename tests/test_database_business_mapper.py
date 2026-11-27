import pytest

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_record,
    record_to_business,
)
from src.lead_intelligence.database.models import BusinessRecord
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus


@pytest.fixture
def business():
    return Business(
        name="Nepal Hiking Team",
        address="Thamel, Kathmandu",
        website="https://www.example.com",
        category="Tour Operator",
        city="Kathmandu",
        district="Kathmandu",
        state="Bagmati",
        country="Nepal",
        country_code="NP",
        serper_cid="123456789",
        latitude=27.7172,
        longitude=85.324,
        extraction_status=ExtractionStatus.SUCCESS,
        website_status="verified",
        website_source="serper_places",
        geographic_sources={
            "city": ["provider_address"],
        },
        geographic_conflicts=["Example conflict"],
        lead_score=85,
        score_version="2",
    )


def test_business_to_record_returns_orm_model(business):
    record = business_to_record(business)

    assert isinstance(record, BusinessRecord)


@pytest.mark.parametrize(
    "field_name",
    [
        "name",
        "address",
        "website",
        "category",
        "city",
        "district",
        "state",
        "country",
        "country_code",
        "serper_cid",
        "latitude",
        "longitude",
        "website_status",
        "website_source",
        "geographic_sources",
        "geographic_conflicts",
        "lead_score",
        "score_version",
    ],
)
def test_business_scalar_fields_are_preserved(
    business,
    field_name,
):
    record = business_to_record(business)

    assert getattr(record, field_name) == getattr(
        business,
        field_name,
    )


def test_business_name_is_normalized(business):
    record = business_to_record(business)

    assert record.name_normalized == "nepal hiking team"


def test_business_address_is_normalized(business):
    record = business_to_record(business)

    assert record.address_normalized == "thamel, kathmandu"


def test_business_domain_is_normalized(business):
    record = business_to_record(business)

    assert record.website_domain == "example.com"


def test_business_extraction_status_is_serialized(business):
    record = business_to_record(business)

    assert record.extraction_status == "success"


def test_minimal_business_mapping():
    record = business_to_record(Business(name="Minimal Business"))

    assert record.name == "Minimal Business"
    assert record.name_normalized == "minimal business"
    assert record.address is None
    assert record.address_normalized is None
    assert record.website_domain is None
    assert record.country_code is None
    assert record.lead_score is None
    assert record.extraction_status == "pending"


def test_unicode_business_name():
    record = business_to_record(Business(name="काठमाडौं यात्रा"))

    assert record.name == "काठमाडौं यात्रा"
    assert record.name_normalized == "काठमाडौं यात्रा"


def test_business_mapping_does_not_mutate_original():
    business = Business(name="Example")

    business.name = "  Example Business  "

    record = business_to_record(business)

    assert record.name == "Example Business"
    assert business.name == "  Example Business  "


def test_geographic_metadata_is_independent(business):
    record = business_to_record(business)

    record.geographic_sources["city"].append("another_source")

    record.geographic_conflicts.append("another_conflict")

    assert business.geographic_sources == {
        "city": ["provider_address"],
    }

    assert business.geographic_conflicts == [
        "Example conflict",
    ]


@pytest.mark.parametrize(
    "value",
    [None, {}, "Business"],
)
def test_business_mapper_rejects_invalid_input(value):
    with pytest.raises(
        PersistenceValidationError,
        match="Business instance",
    ):
        business_to_record(value)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("name", ""),
        ("name", None),
        ("country_code", "INVALID"),
        ("latitude", 91),
        ("longitude", 181),
        ("lead_score", 101),
        ("extraction_status", "invalid"),
        ("emails", None),
    ],
)
def test_business_mapper_revalidates_mutated_objects(
    business,
    field_name,
    value,
):
    setattr(business, field_name, value)

    with pytest.raises(PersistenceValidationError):
        business_to_record(business)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("name", "a" * 513),
        ("address", "a" * 1025),
        ("city", "a" * 513),
        ("name", "Invalid\x00Name"),
        ("category", "Invalid\x00Category"),
        ("website_status", None),
        ("website_status", ""),
        ("website_source", 123),
        ("score_version", True),
    ],
)
def test_business_mapper_rejects_invalid_storage_values(
    business,
    field_name,
    value,
):
    setattr(business, field_name, value)

    with pytest.raises(PersistenceValidationError):
        business_to_record(business)


def test_business_mapper_rejects_invalid_geographic_source(
    business,
):
    business.geographic_sources = {
        "city": ["invalid\x00source"],
    }

    with pytest.raises(PersistenceValidationError):
        business_to_record(business)


def test_business_mapper_rejects_invalid_geographic_key(
    business,
):
    business.geographic_sources = {
        "invalid\x00key": ["source"],
    }

    with pytest.raises(PersistenceValidationError):
        business_to_record(business)


def test_business_mapper_rejects_invalid_geographic_conflict(
    business,
):
    business.geographic_conflicts = [
        "invalid\x00conflict",
    ]

    with pytest.raises(PersistenceValidationError):
        business_to_record(business)


def test_record_to_business_returns_domain_model(business):
    record = business_to_record(business)

    restored = record_to_business(record)

    assert isinstance(restored, Business)


@pytest.mark.parametrize(
    "field_name",
    [
        "name",
        "address",
        "website",
        "category",
        "city",
        "district",
        "state",
        "country",
        "country_code",
        "serper_cid",
        "latitude",
        "longitude",
        "extraction_status",
        "website_status",
        "website_source",
        "geographic_sources",
        "geographic_conflicts",
    ],
)
def test_scalar_business_round_trip(
    business,
    field_name,
):
    record = business_to_record(business)

    restored = record_to_business(record)

    assert getattr(restored, field_name) == getattr(
        business,
        field_name,
    )


def test_scalar_reconstruction_invalidates_score(business):
    record = business_to_record(business)

    restored = record_to_business(record)

    assert restored.lead_score is None
    assert restored.score_version is None
    assert restored.lead_quality is None
    assert restored._score_snapshot is None


def test_scalar_reconstruction_copies_metadata(business):
    record = business_to_record(business)

    restored = record_to_business(record)

    restored.geographic_sources["city"].append("new_source")

    restored.geographic_conflicts.append("new_conflict")

    assert record.geographic_sources == {
        "city": ["provider_address"],
    }

    assert record.geographic_conflicts == [
        "Example conflict",
    ]


@pytest.mark.parametrize(
    "value",
    [None, {}, Business(name="Example")],
)
def test_record_mapper_rejects_invalid_input(value):
    with pytest.raises(
        PersistenceValidationError,
        match="BusinessRecord instance",
    ):
        record_to_business(value)


def test_minimal_business_round_trip():
    original = Business(name="Example")

    restored = record_to_business(business_to_record(original))

    assert restored == original
