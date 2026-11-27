from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from src.lead_intelligence.database.exceptions import PersistenceValidationError
from src.lead_intelligence.database.mappers.business import business_to_complete_record
from src.lead_intelligence.database.repositories.business import BusinessRepository
from src.lead_intelligence.models.business import Business


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def repository(session):
    return BusinessRepository(session)


@pytest.mark.parametrize("city", [None, "Kathmandu"])
def test_list_by_location(repository, session, city):
    record = business_to_complete_record(
        Business(name="Example", country_code="NP", city="Kathmandu")
    )
    session.scalars.return_value.all.return_value = [record]
    businesses = repository.list_by_location("np", city, limit=25, offset=50)
    assert len(businesses) == 1
    assert businesses[0].name == record.name
    assert businesses[0].country_code == "NP"
    compiled = session.scalars.call_args.args[0].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "NP" in compiled.params.values()
    assert "ORDER BY" in sql
    assert "businesses.created_at" in sql
    assert "businesses.id" in sql
    assert "LIMIT" in sql
    assert "OFFSET" in sql
    assert 25 in compiled.params.values()
    assert 50 in compiled.params.values()
    if city is not None:
        assert city in compiled.params.values()
        assert "lower(" in sql


def test_empty_location(repository, session):
    session.scalars.return_value.all.return_value = []
    assert repository.list_by_location("NP") == []


@pytest.mark.parametrize("limit", [None, True, 0, -1, 501, 10.5, "100"])
def test_invalid_limit(repository, session, limit):
    with pytest.raises(PersistenceValidationError, match="Limit"):
        repository.list_by_location("NP", limit=limit)
    session.scalars.assert_not_called()


@pytest.mark.parametrize("offset", [None, True, -1, 1.5, "10", 2_147_483_648])
def test_invalid_offset(repository, session, offset):
    with pytest.raises(PersistenceValidationError, match="Offset"):
        repository.list_by_location("NP", offset=offset)
    session.scalars.assert_not_called()


@pytest.mark.parametrize("country", [None, "", "INVALID", "XX", 123])
def test_invalid_country(repository, session, country):
    with pytest.raises(PersistenceValidationError):
        repository.list_by_location(country)
    session.scalars.assert_not_called()


@pytest.mark.parametrize("city", ["", " ", "\x00", "a" * 513, 123])
def test_invalid_city(repository, session, city):
    with pytest.raises(PersistenceValidationError):
        repository.list_by_location("NP", city)
    session.scalars.assert_not_called()


@pytest.mark.parametrize(("city", "count"), [(None, 25), ("Kathmandu", 10), (None, 0)])
def test_count_by_location(repository, session, city, count):
    session.execute.return_value.scalar_one.return_value = count
    assert repository.count_by_location("NP", city) == count
    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "count(" in str(compiled)
    assert "NP" in compiled.params.values()
    if city is not None:
        assert city in compiled.params.values()


def test_count_invalid_country(repository, session):
    with pytest.raises(PersistenceValidationError):
        repository.count_by_location("INVALID")
    session.execute.assert_not_called()


def test_get_record_for_update(repository, session):
    record = business_to_complete_record(Business(name="Example"))
    record.id = uuid4()
    session.execute.return_value.scalar_one_or_none.return_value = record
    assert repository.get_record_for_update(record.id) is record
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "FOR UPDATE OF" in str(compiled)
    assert record.id in compiled.params.values()
    assert statement.get_execution_options()["populate_existing"] is True


def test_get_record_for_update_missing(repository, session):
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert repository.get_record_for_update(uuid4()) is None


def test_get_record_for_update_invalid_id(repository, session):
    with pytest.raises(PersistenceValidationError):
        repository.get_record_for_update("invalid-uuid")
    session.execute.assert_not_called()


def test_queries_do_not_own_transactions(repository, session):
    session.scalars.return_value.all.return_value = []
    session.execute.return_value.scalar_one.return_value = 0
    repository.list_by_location("NP")
    repository.count_by_location("NP")
    repository.get_record_for_update(uuid4())
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
