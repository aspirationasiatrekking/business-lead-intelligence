import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex, CreateTable

from src.lead_intelligence.database.base import (
    DATABASE_SCHEMA,
    Base,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    BusinessRecord,
    BusinessSourceRecord,
    ContactSourceRecord,
    ProcessingFailureRecord,
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.models.extraction_status import ExtractionStatus

MODELS = (
    BusinessRecord,
    BusinessContactRecord,
    BusinessSourceRecord,
    ContactSourceRecord,
    SearchQueryRecord,
    SearchJobRecord,
    SearchResultRecord,
    ProcessingFailureRecord,
)

EXPECTED_TABLES = {
    "businesses",
    "business_contacts",
    "business_sources",
    "contact_sources",
    "search_queries",
    "search_jobs",
    "search_results",
    "processing_failures",
    "users",
    "user_sessions",
}


def get_constraint(model, name):
    return next(
        constraint
        for constraint in model.__table__.constraints
        if constraint.name == name
    )


def test_all_application_tables_registered():
    actual = {
        table.name
        for table in Base.metadata.tables.values()
        if table.schema == DATABASE_SCHEMA
    }

    assert actual == EXPECTED_TABLES


def test_orm_relationship_configuration():
    configure_mappers()


@pytest.mark.parametrize("model", MODELS)
def test_models_use_application_schema(model):
    assert model.__table__.schema == DATABASE_SCHEMA


@pytest.mark.parametrize("model", MODELS)
def test_models_have_uuid_primary_key(model):
    column = model.__table__.c.id

    assert column.primary_key
    assert column.type.as_uuid is True
    assert column.default is not None


@pytest.mark.parametrize("model", MODELS)
def test_postgresql_table_compilation(model):
    ddl = str(
        CreateTable(model.__table__).compile(
            dialect=postgresql.dialect(),
        )
    )

    assert f"{DATABASE_SCHEMA}.{model.__tablename__}" in ddl
    assert "PRIMARY KEY" in ddl
    assert "UUID" in ddl


@pytest.mark.parametrize("model", MODELS)
def test_postgresql_index_compilation(model):
    for index in model.__table__.indexes:
        ddl = str(
            CreateIndex(index).compile(
                dialect=postgresql.dialect(),
            )
        )

        assert "CREATE INDEX" in ddl or "CREATE UNIQUE INDEX" in ddl


@pytest.mark.parametrize(
    ("model", "column", "target", "ondelete"),
    [
        (
            BusinessContactRecord,
            "business_id",
            "businesses.id",
            "CASCADE",
        ),
        (
            BusinessSourceRecord,
            "business_id",
            "businesses.id",
            "CASCADE",
        ),
        (
            ContactSourceRecord,
            "contact_id",
            "business_contacts.id",
            "CASCADE",
        ),
        (
            SearchJobRecord,
            "query_id",
            "search_queries.id",
            "RESTRICT",
        ),
        (
            SearchResultRecord,
            "job_id",
            "search_jobs.id",
            "CASCADE",
        ),
        (
            SearchResultRecord,
            "business_id",
            "businesses.id",
            "RESTRICT",
        ),
        (
            ProcessingFailureRecord,
            "job_id",
            "search_jobs.id",
            "CASCADE",
        ),
        (
            ProcessingFailureRecord,
            "business_id",
            "businesses.id",
            "SET NULL",
        ),
    ],
)
def test_foreign_key_constraints(
    model,
    column,
    target,
    ondelete,
):
    foreign_keys = model.__table__.c[column].foreign_keys

    assert len(foreign_keys) == 1

    foreign_key = next(iter(foreign_keys))

    assert foreign_key.column.table.schema == DATABASE_SCHEMA

    assert f"{foreign_key.column.table.name}.{foreign_key.column.name}" == target

    assert foreign_key.ondelete == ondelete


@pytest.mark.parametrize(
    ("model", "name", "columns"),
    [
        (
            SearchQueryRecord,
            "uq_search_queries_signature",
            (
                "country_code",
                "city_normalized",
                "query_normalized",
            ),
        ),
        (
            BusinessContactRecord,
            "uq_business_contacts_identity",
            (
                "business_id",
                "contact_type",
                "normalized_value",
            ),
        ),
        (
            BusinessSourceRecord,
            "uq_business_sources_identity",
            (
                "business_id",
                "source_type",
                "source_url",
            ),
        ),
        (
            ContactSourceRecord,
            "uq_contact_sources_identity",
            (
                "contact_id",
                "source_url",
            ),
        ),
        (
            SearchResultRecord,
            "uq_search_results_job_business",
            ("job_id", "business_id"),
        ),
        (
            SearchResultRecord,
            "uq_search_results_job_position",
            ("job_id", "position"),
        ),
    ],
)
def test_composite_uniqueness_constraints(
    model,
    name,
    columns,
):
    constraint = get_constraint(model, name)

    assert isinstance(constraint, UniqueConstraint)
    assert tuple(constraint.columns.keys()) == columns


@pytest.mark.parametrize(
    "column",
    ["website", "website_domain", "serper_cid"],
)
def test_business_identity_fields_are_not_globally_unique(column):
    table = BusinessRecord.__table__

    assert not table.c[column].unique

    assert not any(
        isinstance(constraint, UniqueConstraint)
        and tuple(constraint.columns.keys()) == (column,)
        for constraint in table.constraints
    )

    assert not any(
        index.unique and tuple(index.columns.keys()) == (column,)
        for index in table.indexes
    )


@pytest.mark.parametrize(
    "column",
    [
        "address",
        "website",
        "city",
        "district",
        "state",
        "country",
        "country_code",
        "latitude",
        "longitude",
        "serper_cid",
        "lead_score",
    ],
)
def test_unknown_business_values_are_nullable(column):
    assert BusinessRecord.__table__.c[column].nullable


@pytest.mark.parametrize(
    ("model", "column"),
    [
        (BusinessRecord, "geographic_sources"),
        (BusinessRecord, "geographic_conflicts"),
        (SearchJobRecord, "search_metrics"),
        (SearchJobRecord, "warnings"),
    ],
)
def test_structured_metadata_uses_jsonb(model, column):
    field = model.__table__.c[column]

    assert isinstance(field.type, JSONB)
    assert not field.nullable
    assert field.server_default is not None


@pytest.mark.parametrize(
    "model",
    [BusinessRecord, SearchResultRecord],
)
def test_extraction_status_constraint_matches_domain(model):
    constraint = get_constraint(
        model,
        f"ck_{model.__tablename__}_extraction_status",
    )

    assert isinstance(constraint, CheckConstraint)

    expression = str(constraint.sqltext)

    for status in ExtractionStatus:
        assert f"'{status.value}'" in expression


def test_score_constraint_exists():
    constraint = get_constraint(
        BusinessRecord,
        "ck_businesses_lead_score_range",
    )

    assert "BETWEEN 0 AND 100" in str(constraint.sqltext)


def test_search_limit_constraint_exists():
    constraint = get_constraint(
        SearchJobRecord,
        "ck_search_jobs_max_results_range",
    )

    assert "BETWEEN 1 AND 100" in str(constraint.sqltext)


def test_serper_cid_supports_unsigned_64_bit_values():
    column = BusinessRecord.__table__.c.serper_cid

    assert column.type.length == 20

    constraint = get_constraint(
        BusinessRecord,
        "ck_businesses_serper_cid_range",
    )

    assert "18446744073709551615" in str(constraint.sqltext)


def test_business_relationships_prevent_implicit_queries():
    configure_mappers()

    assert BusinessRecord.contacts.property.lazy == "raise"
    assert BusinessRecord.sources.property.lazy == "raise"


def test_business_identity_indexes():
    table = BusinessRecord.__table__

    indexes = {tuple(index.columns.keys()) for index in table.indexes}

    assert ("serper_cid",) in indexes
    assert ("website_domain",) in indexes
    assert ("name_normalized", "address_normalized") in indexes
    assert ("country_code", "city") in indexes


def test_contact_candidate_lookup_index():
    indexes = {
        tuple(index.columns.keys()) for index in BusinessContactRecord.__table__.indexes
    }

    assert ("contact_type", "normalized_value") in indexes


def test_database_metadata_dependency_order():
    positions = {
        table.name: index for index, table in enumerate(Base.metadata.sorted_tables)
    }

    assert positions["businesses"] < positions["business_contacts"]
    assert positions["business_contacts"] < positions["contact_sources"]
    assert positions["search_queries"] < positions["search_jobs"]
    assert positions["search_jobs"] < positions["search_results"]
    assert positions["businesses"] < positions["search_results"]


@pytest.mark.parametrize(
    ("model", "name", "expression"),
    [
        (
            BusinessRecord,
            "normalized_name_bytes",
            "octet_length(name_normalized) <= 512",
        ),
        (
            BusinessRecord,
            "normalized_address_bytes",
            "octet_length(address_normalized) <= 1024",
        ),
        (
            BusinessRecord,
            "website_domain_bytes",
            "octet_length(website_domain) <= 253",
        ),
        (
            BusinessRecord,
            "city_bytes",
            "octet_length(city) <= 512",
        ),
        (
            BusinessContactRecord,
            "normalized_value_bytes",
            "octet_length(normalized_value) <= 512",
        ),
        (
            BusinessSourceRecord,
            "source_url_bytes",
            "octet_length(source_url) <= 2048",
        ),
        (
            ContactSourceRecord,
            "source_url_bytes",
            "octet_length(source_url) <= 2048",
        ),
        (
            SearchQueryRecord,
            "signature_bytes",
            "octet_length(city_normalized) + octet_length(query_normalized) <= 2048",
        ),
    ],
)
def test_indexed_text_byte_constraints(
    model,
    name,
    expression,
):
    constraint = get_constraint(
        model,
        f"ck_{model.__tablename__}_{name}",
    )

    assert isinstance(constraint, CheckConstraint)
    assert str(constraint.sqltext) == expression

    ddl = str(
        CreateTable(model.__table__).compile(
            dialect=postgresql.dialect(),
        )
    )

    assert expression in ddl


def test_normalized_business_name_cannot_be_empty():
    constraint = get_constraint(
        BusinessRecord,
        "ck_businesses_nonempty_normalized_name",
    )

    assert isinstance(constraint, CheckConstraint)

    assert str(constraint.sqltext) == ("length(btrim(name_normalized)) > 0")


@pytest.mark.parametrize(
    "column",
    [
        "address_normalized",
        "website_domain",
        "city",
    ],
)
def test_indexed_optional_business_fields_remain_nullable(
    column,
):
    assert BusinessRecord.__table__.c[column].nullable


def test_business_name_address_index_byte_budget():
    name_constraint = get_constraint(
        BusinessRecord,
        "ck_businesses_normalized_name_bytes",
    )

    address_constraint = get_constraint(
        BusinessRecord,
        "ck_businesses_normalized_address_bytes",
    )

    name_limit = int(str(name_constraint.sqltext).rsplit(" ", 1)[-1])

    address_limit = int(str(address_constraint.sqltext).rsplit(" ", 1)[-1])

    assert name_limit + address_limit <= 2048
