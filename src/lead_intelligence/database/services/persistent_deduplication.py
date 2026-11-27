from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from src.lead_intelligence.database.exceptions import PersistenceConflictError
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
    business_to_record,
    complete_record_to_business,
)
from src.lead_intelligence.database.models import BusinessContactRecord, BusinessRecord
from src.lead_intelligence.database.repositories.contact import ContactRepository
from src.lead_intelligence.database.repositories.observations import touch_observation
from src.lead_intelligence.database.repositories.source import SourceRepository
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)

# All canonical business writers must acquire this transaction-scoped lock.
WRITE_LOCK = 731605219
MAX_CANDIDATES = 500


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    business_id: UUID
    created: bool
    ambiguous: bool = False


def candidate_statement(incoming: BusinessRecord):
    conditions = []
    if incoming.serper_cid:
        conditions.append(BusinessRecord.serper_cid == incoming.serper_cid)
    if incoming.website_domain:
        conditions.append(BusinessRecord.website_domain == incoming.website_domain)
    if incoming.address_normalized:
        conditions.append(
            and_(
                BusinessRecord.name_normalized == incoming.name_normalized,
                BusinessRecord.address_normalized == incoming.address_normalized,
            )
        )
    phones = {
        contact.normalized_value
        for contact in incoming.contacts
        if contact.contact_type == "phone"
        and BusinessDeduplicationService.normalize_phone(contact.normalized_value)
        == contact.normalized_value
    }
    if phones:
        conditions.append(
            BusinessRecord.contacts.any(
                and_(
                    BusinessContactRecord.contact_type == "phone",
                    BusinessContactRecord.normalized_value.in_(sorted(phones)),
                )
            )
        )
    if not conditions:
        return None
    return (
        select(BusinessRecord)
        .where(or_(*conditions))
        .options(
            selectinload(BusinessRecord.contacts).selectinload(
                BusinessContactRecord.sources
            ),
            selectinload(BusinessRecord.sources),
        )
        .order_by(BusinessRecord.id)
        .limit(MAX_CANDIDATES + 1)
        .execution_options(populate_existing=True)
    )


class PersistentDeduplicationService:
    """Serialize canonical writes; caller owns commit and rollback."""

    def __init__(self, session: Session):
        self.session = session
        self.dedup = BusinessDeduplicationService()

    def _lock(self) -> None:
        if self.session.new or self.session.dirty or self.session.deleted:
            raise PersistenceConflictError("Flush pending changes before persistence.")
        if self.session.scalar(text("SHOW transaction_isolation")) != "read committed":
            raise PersistenceConflictError("Persistence requires READ COMMITTED.")
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK}
        )

    def _matches(self, incoming: BusinessRecord, domain: Business):
        statement = candidate_statement(incoming)
        if statement is None:
            return []
        candidates = self.session.scalars(statement).all()
        if len(candidates) > MAX_CANDIDATES:
            raise PersistenceConflictError("Too many business identity candidates.")
        matches = [
            (record, restored)
            for record in candidates
            if self.dedup.are_duplicates(
                restored := complete_record_to_business(record), domain
            )
        ]
        exact = [
            pair
            for pair in matches
            if incoming.serper_cid and pair[0].serper_cid == incoming.serper_cid
        ]
        return exact or matches

    @staticmethod
    def _stamp_new(record: BusinessRecord, observed_at: datetime) -> None:
        touch_observation(record, observed_at)
        for contact in record.contacts:
            touch_observation(contact, observed_at)
            for source in contact.sources:
                touch_observation(source, observed_at)
        for source in record.sources:
            touch_observation(source, observed_at)

    def persist(
        self, business: Business, *, region: str | None = None
    ) -> PersistenceResult:
        incoming = business_to_complete_record(business, region=region)
        domain = complete_record_to_business(incoming)
        self._lock()
        matches = self._matches(incoming, domain)
        observed_at = self.session.scalar(select(func.clock_timestamp()))
        if len(matches) != 1:
            self._stamp_new(incoming, observed_at)
            self.session.add(incoming)
            self.session.flush()
            return PersistenceResult(incoming.id, True, len(matches) > 1)

        record, existing = matches[0]
        merged = self.dedup.merge_business(existing, domain)
        scalar = business_to_record(merged)
        for column in (
            "name",
            "name_normalized",
            "address",
            "address_normalized",
            "website",
            "website_domain",
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
        ):
            setattr(record, column, getattr(scalar, column))
        # Only incoming evidence is observed again, not the historical union.
        ContactRepository().merge(record, incoming.contacts, observed_at=observed_at)
        SourceRepository().merge(record, incoming.sources, observed_at=observed_at)
        touch_observation(record, observed_at)
        restored = complete_record_to_business(record)
        record.lead_score = restored.lead_score
        record.score_version = restored.score_version
        self.session.flush()
        return PersistenceResult(record.id, False)
