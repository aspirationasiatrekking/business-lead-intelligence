from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
)
from src.lead_intelligence.database.models import BusinessRecord
from src.lead_intelligence.database.repositories.business import (
    BusinessRepository,
)
from src.lead_intelligence.models.business import Business


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def repository(session):
    return BusinessRepository(session)


@pytest.fixture
def business():
    return Business(
        name="Example Trekking Company",
        website="https://company.com",
        country_code="NP",
        city="Kathmandu",
        emails=["info@company.com"],
        phone_numbers=["+9779846041887"],
        contact_page_urls=[
            "https://company.com/contact",
        ],
    )


@pytest.fixture
def record(business):
    result = business_to_complete_record(business)
    result.id = uuid4()

    return result


def test_repository_accepts_session(session):
    repository = BusinessRepository(session)

    assert repository.session is session


@pytest.mark.parametrize(
    "value",
    [None, {}, "session"],
)
def test_repository_rejects_invalid_session(value):
    with pytest.raises(
        TypeError,
        match="SQLAlchemy Session",
    ):
        BusinessRepository(value)


def test_create_returns_business_record(repository, business):
    record = repository.create(business)

    assert isinstance(record, BusinessRecord)
    assert record.name == business.name


def test_create_maps_contacts_and_sources(
    repository,
    business,
):
    record = repository.create(business)

    assert len(record.contacts) == 2
    assert len(record.sources) == 2


def test_create_adds_record(
    repository,
    session,
    business,
):
    record = repository.create(business)

    session.add.assert_called_once_with(record)


def test_create_flushes_session(
    repository,
    session,
    business,
):
    repository.create(business)

    session.flush.assert_called_once_with()


def test_create_does_not_own_transaction(
    repository,
    session,
    business,
):
    repository.create(business)

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_create_rejects_invalid_business(
    repository,
    session,
):
    with pytest.raises(PersistenceValidationError):
        repository.create(None)

    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_create_passes_search_region(repository):
    business = Business(
        name="Example",
        phone_numbers=["9846041887"],
    )

    record = repository.create(
        business,
        region="NP",
    )

    assert record.contacts[0].normalized_value == ("+9779846041887")


def test_create_propagates_database_failure(
    repository,
    session,
    business,
):
    session.flush.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("Simulated integrity error"),
    )

    with pytest.raises(IntegrityError):
        repository.create(business)

    session.rollback.assert_not_called()
    session.commit.assert_not_called()


def test_get_record_by_id(
    repository,
    session,
    record,
):
    session.execute.return_value.scalar_one_or_none.return_value = record

    result = repository.get_record_by_id(record.id)

    assert result is record
    session.execute.assert_called_once()


def test_get_record_returns_none_when_missing(
    repository,
    session,
):
    session.execute.return_value.scalar_one_or_none.return_value = None

    assert repository.get_record_by_id(uuid4()) is None


def test_get_record_filters_by_uuid(
    repository,
    session,
):
    business_id = uuid4()

    repository.get_record_by_id(business_id)

    statement = session.execute.call_args.args[0]

    compiled = statement.compile(
        dialect=postgresql.dialect(),
    )

    assert "lead_intelligence.businesses.id" in str(compiled)

    assert "WHERE" in str(compiled)
    assert business_id in compiled.params.values()


def test_complete_statement_selects_businesses(
    repository,
):
    statement = repository._complete_record_statement()

    compiled = statement.compile(
        dialect=postgresql.dialect(),
    )

    assert "FROM lead_intelligence.businesses" in str(compiled)


def test_get_by_id_reconstructs_business(
    repository,
    session,
    record,
):
    session.execute.return_value.scalar_one_or_none.return_value = record

    business = repository.get_by_id(record.id)

    assert isinstance(business, Business)
    assert business.name == record.name

    assert business.emails == [
        "info@company.com",
    ]

    assert business.phone_numbers == [
        "+9779846041887",
    ]


def test_get_by_id_returns_none_when_missing(
    repository,
    session,
):
    session.execute.return_value.scalar_one_or_none.return_value = None

    assert repository.get_by_id(uuid4()) is None


def test_get_by_id_does_not_commit(
    repository,
    session,
    record,
):
    session.execute.return_value.scalar_one_or_none.return_value = record

    repository.get_by_id(record.id)

    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_exists_returns_true(
    repository,
    session,
):
    business_id = uuid4()

    session.execute.return_value.scalar_one_or_none.return_value = business_id

    assert repository.exists(business_id) is True


def test_exists_returns_false(
    repository,
    session,
):
    session.execute.return_value.scalar_one_or_none.return_value = None

    assert repository.exists(uuid4()) is False


@pytest.mark.parametrize(
    "method_name",
    [
        "get_record_by_id",
        "get_by_id",
        "exists",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        None,
        "not-a-uuid",
        123,
        True,
    ],
)
def test_repository_rejects_invalid_ids(
    repository,
    session,
    method_name,
    value,
):
    method = getattr(repository, method_name)

    with pytest.raises(
        PersistenceValidationError,
        match="UUID",
    ):
        method(value)

    session.execute.assert_not_called()
