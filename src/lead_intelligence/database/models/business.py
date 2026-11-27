from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.lead_intelligence.database.base import Base
from src.lead_intelligence.database.models.common import (
    EXTRACTION_STATUS_VALUES,
    MAX_BUSINESS_CITY_BYTES,
    MAX_NORMALIZED_ADDRESS_BYTES,
    MAX_NORMALIZED_CONTACT_BYTES,
    MAX_NORMALIZED_NAME_BYTES,
    MAX_SOURCE_URL_BYTES,
    MAX_WEBSITE_DOMAIN_BYTES,
    ObservationMixin,
    TimestampMixin,
    UUIDMixin,
)
from src.lead_intelligence.models.extraction_status import ExtractionStatus


class BusinessRecord(
    UUIDMixin,
    TimestampMixin,
    ObservationMixin,
    Base,
):
    """Canonical stored representation of a discovered business."""

    __tablename__ = "businesses"

    __table_args__ = (
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="nonempty_name",
        ),
        CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name="country_code_format",
        ),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="longitude_range",
        ),
        CheckConstraint(
            "lead_score IS NULL OR lead_score BETWEEN 0 AND 100",
            name="lead_score_range",
        ),
        CheckConstraint(
            f"extraction_status IN ({EXTRACTION_STATUS_VALUES})",
            name="extraction_status",
        ),
        CheckConstraint(
            """
            CASE
                WHEN serper_cid IS NULL THEN TRUE
                WHEN serper_cid ~ '^[1-9][0-9]{0,19}$'
                    THEN CAST(serper_cid AS numeric)
                         <= 18446744073709551615
                ELSE FALSE
            END
            """,
            name="serper_cid_range",
        ),
        CheckConstraint(
            "jsonb_typeof(geographic_sources) = 'object'",
            name="geographic_sources_type",
        ),
        CheckConstraint(
            "jsonb_typeof(geographic_conflicts) = 'array'",
            name="geographic_conflicts_type",
        ),
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="observation_order",
        ),
        CheckConstraint(
            "length(btrim(name_normalized)) > 0",
            name="nonempty_normalized_name",
        ),
        CheckConstraint(
            f"octet_length(name_normalized) <= {MAX_NORMALIZED_NAME_BYTES}",
            name="normalized_name_bytes",
        ),
        CheckConstraint(
            f"octet_length(address_normalized) <= {MAX_NORMALIZED_ADDRESS_BYTES}",
            name="normalized_address_bytes",
        ),
        CheckConstraint(
            f"octet_length(website_domain) <= {MAX_WEBSITE_DOMAIN_BYTES}",
            name="website_domain_bytes",
        ),
        CheckConstraint(
            f"octet_length(city) <= {MAX_BUSINESS_CITY_BYTES}",
            name="city_bytes",
        ),
        Index(
            "ix_businesses_country_city",
            "country_code",
            "city",
        ),
        Index(
            "ix_businesses_name_address",
            "name_normalized",
            "address_normalized",
        ),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)

    address: Mapped[str | None] = mapped_column(Text)
    address_normalized: Mapped[str | None] = mapped_column(Text)

    website: Mapped[str | None] = mapped_column(Text)

    website_domain: Mapped[str | None] = mapped_column(
        Text,
        index=True,
    )

    category: Mapped[str | None] = mapped_column(Text)

    city: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(String(2))

    serper_cid: Mapped[str | None] = mapped_column(
        String(20),
        index=True,
    )

    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)

    extraction_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ExtractionStatus.PENDING.value,
        server_default=ExtractionStatus.PENDING.value,
    )

    website_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="unknown",
        server_default="unknown",
    )

    website_source: Mapped[str | None] = mapped_column(Text)

    geographic_sources: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    geographic_conflicts: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    lead_score: Mapped[int | None] = mapped_column(SmallInteger)
    score_version: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["BusinessContactRecord"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    sources: Mapped[list["BusinessSourceRecord"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class BusinessContactRecord(
    UUIDMixin,
    ObservationMixin,
    Base,
):
    """A contact belonging to a specific business."""

    __tablename__ = "business_contacts"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "contact_type",
            "normalized_value",
            name="uq_business_contacts_identity",
        ),
        CheckConstraint(
            "contact_type IN ('email', 'phone')",
            name="contact_type",
        ),
        CheckConstraint(
            "length(btrim(value)) > 0",
            name="nonempty_value",
        ),
        CheckConstraint(
            "length(btrim(normalized_value)) > 0",
            name="nonempty_normalized_value",
        ),
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="observation_order",
        ),
        CheckConstraint(
            f"octet_length(normalized_value) <= {MAX_NORMALIZED_CONTACT_BYTES}",
            name="normalized_value_bytes",
        ),
        Index(
            "ix_business_contacts_lookup",
            "contact_type",
            "normalized_value",
        ),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "businesses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    contact_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(Text, nullable=False)

    normalized_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    business: Mapped[BusinessRecord] = relationship(
        back_populates="contacts",
        lazy="raise",
    )

    sources: Mapped[list["ContactSourceRecord"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class BusinessSourceRecord(
    UUIDMixin,
    ObservationMixin,
    Base,
):
    """Discovery and website evidence associated with a business."""

    __tablename__ = "business_sources"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "source_type",
            "source_url",
            name="uq_business_sources_identity",
        ),
        CheckConstraint(
            "source_type IN ('discovery', 'website', 'contact_page')",
            name="source_type",
        ),
        CheckConstraint(
            "length(btrim(source_url)) > 0",
            name="nonempty_source_url",
        ),
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="observation_order",
        ),
        CheckConstraint(
            f"octet_length(source_url) <= {MAX_SOURCE_URL_BYTES}",
            name="source_url_bytes",
        ),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "businesses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    verification_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="unknown",
        server_default="unknown",
    )

    business: Mapped[BusinessRecord] = relationship(
        back_populates="sources",
        lazy="raise",
    )


class ContactSourceRecord(
    UUIDMixin,
    ObservationMixin,
    Base,
):
    """Source evidence for an individual email or phone number."""

    __tablename__ = "contact_sources"

    __table_args__ = (
        UniqueConstraint(
            "contact_id",
            "source_url",
            name="uq_contact_sources_identity",
        ),
        CheckConstraint(
            "length(btrim(source_url)) > 0",
            name="nonempty_source_url",
        ),
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="observation_order",
        ),
        CheckConstraint(
            f"octet_length(source_url) <= {MAX_SOURCE_URL_BYTES}",
            name="source_url_bytes",
        ),
    )

    contact_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "business_contacts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    contact: Mapped[BusinessContactRecord] = relationship(
        back_populates="sources",
        lazy="raise",
    )
