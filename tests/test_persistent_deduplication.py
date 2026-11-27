from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from src.lead_intelligence.database.exceptions import PersistenceConflictError
from src.lead_intelligence.database.mappers.business import business_to_complete_record
from src.lead_intelligence.database.services.persistent_deduplication import (
    MAX_CANDIDATES,
    PersistentDeduplicationService,
    candidate_statement,
)
from src.lead_intelligence.models.business import Business

NOW = datetime(2026, 11, 27, tzinfo=UTC)


@pytest.fixture
def session():
    session = MagicMock(spec=Session)
    session.new = set()
    session.dirty = set()
    session.deleted = set()
    session.scalar.side_effect = ["read committed", NOW]
    session.scalars.return_value.all.return_value = []
    session.add.side_effect = lambda record: setattr(record, "id", uuid4())
    return session


def make_record(**kwargs):
    record = business_to_complete_record(Business(name="Example", **kwargs))
    record.id = uuid4()
    PersistentDeduplicationService._stamp_new(record, NOW - timedelta(days=1))
    return record


def test_no_identity_has_no_candidate_query():
    assert candidate_statement(make_record()) is None


def test_candidate_query_uses_identity_keys():
    record = make_record(
        website="https://company.com",
        address="Thamel",
        serper_cid="123",
        phone_numbers=["+9779846041887"],
    )
    statement = candidate_statement(record)
    sql = str(statement.compile(dialect=postgresql.dialect()))
    for key in (
        "serper_cid",
        "website_domain",
        "address_normalized",
        "normalized_value",
    ):
        assert key in sql
    assert "EXISTS" in sql
    assert "LIMIT" in sql


def test_new_business(session):
    result = PersistentDeduplicationService(session).persist(Business(name="New"))
    assert result.created and not result.ambiguous
    assert result.business_id == session.add.call_args.args[0].id
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_merge_preserves_old_contacts_and_observation(session):
    record = make_record(
        website="https://company.com",
        emails=["info@company.com"],
        phone_numbers=["+9779846041887"],
    )
    phone = record.contacts[1]
    session.scalars.return_value.all.return_value = [record]
    result = PersistentDeduplicationService(session).persist(
        Business(
            name="Example",
            website="https://company.com",
            emails=["sales@company.com"],
            address="Thamel",
            category="Tour operator",
        )
    )
    assert not result.created
    assert result.business_id == record.id
    assert record.address == "Thamel"
    assert record.lead_score == 100
    assert len(record.contacts) == 3
    assert phone.last_seen_at == NOW - timedelta(days=1)
    assert record.last_seen_at == NOW
    session.add.assert_not_called()


def test_conflicting_address_creates_new(session):
    session.scalars.return_value.all.return_value = [
        make_record(website="https://company.com", address="Pokhara")
    ]
    result = PersistentDeduplicationService(session).persist(
        Business(name="Example", website="https://company.com", address="Kathmandu")
    )
    assert result.created and not result.ambiguous


def test_ambiguous_matches_create_separate(session):
    session.scalars.return_value.all.return_value = [
        make_record(website="https://company.com") for _ in range(2)
    ]
    result = PersistentDeduplicationService(session).persist(
        Business(name="Example", website="https://company.com")
    )
    assert result.created and result.ambiguous


def test_exact_cid_preferred(session):
    exact = make_record(website="https://company.com", serper_cid="123")
    session.scalars.return_value.all.return_value = [
        make_record(website="https://company.com"),
        exact,
    ]
    result = PersistentDeduplicationService(session).persist(
        Business(name="Example", website="https://company.com", serper_cid="123")
    )
    assert result.business_id == exact.id and not result.created


def test_candidate_overflow_fails_closed(session):
    session.scalars.return_value.all.return_value = [None] * (MAX_CANDIDATES + 1)
    with pytest.raises(PersistenceConflictError, match="Too many"):
        PersistentDeduplicationService(session).persist(
            Business(name="Example", website="https://company.com")
        )
    session.add.assert_not_called()


def test_pending_changes_rejected(session):
    session.new = {object()}
    with pytest.raises(PersistenceConflictError, match="Flush"):
        PersistentDeduplicationService(session).persist(Business(name="Example"))
    session.execute.assert_not_called()


def test_wrong_isolation_rejected(session):
    session.scalar.side_effect = ["repeatable read"]
    with pytest.raises(PersistenceConflictError, match="READ COMMITTED"):
        PersistentDeduplicationService(session).persist(Business(name="Example"))
    session.execute.assert_not_called()
