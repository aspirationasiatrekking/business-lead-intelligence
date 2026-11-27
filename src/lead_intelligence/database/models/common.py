from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.lead_intelligence.models.extraction_status import ExtractionStatus

EXTRACTION_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ExtractionStatus)

# Maximum UTF-8 byte lengths for indexed text values.
MAX_NORMALIZED_NAME_BYTES = 512
MAX_NORMALIZED_ADDRESS_BYTES = 1024
MAX_WEBSITE_DOMAIN_BYTES = 253
MAX_BUSINESS_CITY_BYTES = 512
MAX_NORMALIZED_CONTACT_BYTES = 512
MAX_SOURCE_URL_BYTES = 2048
MAX_SEARCH_SIGNATURE_BYTES = 2048


class UUIDMixin:
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ObservationMixin:
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
