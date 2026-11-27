from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
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
from src.lead_intelligence.database.models.business import BusinessRecord
from src.lead_intelligence.database.models.common import (
    EXTRACTION_STATUS_VALUES,
    MAX_SEARCH_SIGNATURE_BYTES,
    CreatedAtMixin,
    TimestampMixin,
    UUIDMixin,
)


class SearchQueryRecord(
    UUIDMixin,
    CreatedAtMixin,
    Base,
):
    """A normalized logical search, independent of execution count."""

    __tablename__ = "search_queries"

    __table_args__ = (
        UniqueConstraint(
            "country_code",
            "city_normalized",
            "query_normalized",
            name="uq_search_queries_signature",
        ),
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="country_code_format",
        ),
        CheckConstraint(
            "length(btrim(city)) BETWEEN 1 AND 100",
            name="city_length",
        ),
        CheckConstraint(
            "length(btrim(query)) BETWEEN 1 AND 250",
            name="query_length",
        ),
        CheckConstraint(
            "length(btrim(city_normalized)) > 0",
            name="nonempty_normalized_city",
        ),
        CheckConstraint(
            "length(btrim(query_normalized)) > 0",
            name="nonempty_normalized_query",
        ),
        CheckConstraint(
            "octet_length(city_normalized) + "
            f"octet_length(query_normalized) <= {MAX_SEARCH_SIGNATURE_BYTES}",
            name="signature_bytes",
        ),
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    city_normalized: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    query: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    query_normalized: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    jobs: Mapped[list["SearchJobRecord"]] = relationship(
        back_populates="query",
        passive_deletes="all",
        lazy="raise",
    )


class SearchJobRecord(
    UUIDMixin,
    TimestampMixin,
    Base,
):
    """An individual execution of a logical search query."""

    __tablename__ = "search_jobs"

    __table_args__ = (
        CheckConstraint(
            "max_results BETWEEN 1 AND 100",
            name="max_results_range",
        ),
        CheckConstraint(
            """
            status IN (
                'queued',
                'running',
                'completed',
                'partial',
                'failed',
                'cancelled'
            )
            """,
            name="job_status",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR "
            "(duration_seconds >= 0 AND "
            "duration_seconds < 'Infinity'::double precision)",
            name="duration_range",
        ),
        CheckConstraint(
            "reported_credits >= 0",
            name="nonnegative_credits",
        ),
        CheckConstraint(
            "unknown_credit_responses >= 0",
            name="nonnegative_unknown_credits",
        ),
        CheckConstraint(
            "jsonb_typeof(search_metrics) = 'object'",
            name="search_metrics_type",
        ),
        CheckConstraint(
            "jsonb_typeof(warnings) = 'array'",
            name="warnings_type",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= created_at",
            name="start_time_order",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name="completion_time_order",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="execution_time_order",
        ),
        Index(
            "ix_search_jobs_query_created",
            "query_id",
            "created_at",
        ),
        Index(
            "ix_search_jobs_status_created",
            "status",
            "created_at",
        ),
    )

    query_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("search_queries.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )

    max_results: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default="queued",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    duration_seconds: Mapped[float | None] = mapped_column(Double)

    reported_credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    unknown_credit_responses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    search_metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    warnings: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    stop_reason: Mapped[str | None] = mapped_column(Text)

    query: Mapped[SearchQueryRecord] = relationship(
        back_populates="jobs",
        lazy="raise",
    )

    results: Mapped[list["SearchResultRecord"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    failures: Mapped[list["ProcessingFailureRecord"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class SearchResultRecord(
    UUIDMixin,
    CreatedAtMixin,
    Base,
):
    """Association between a search execution and a stored business."""

    __tablename__ = "search_results"

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "business_id",
            name="uq_search_results_job_business",
        ),
        UniqueConstraint(
            "job_id",
            "position",
            name="uq_search_results_job_position",
        ),
        CheckConstraint(
            "position BETWEEN 1 AND 100",
            name="position_range",
        ),
        CheckConstraint(
            "lead_score_at_discovery IS NULL OR "
            "lead_score_at_discovery BETWEEN 0 AND 100",
            name="discovery_score_range",
        ),
        CheckConstraint(
            f"extraction_status IN ({EXTRACTION_STATUS_VALUES})",
            name="extraction_status",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("search_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    lead_score_at_discovery: Mapped[int | None] = mapped_column(
        SmallInteger,
    )

    score_version: Mapped[str | None] = mapped_column(Text)

    job: Mapped[SearchJobRecord] = relationship(
        back_populates="results",
        lazy="raise",
    )

    business: Mapped[BusinessRecord] = relationship(
        lazy="raise",
    )


class ProcessingFailureRecord(
    UUIDMixin,
    CreatedAtMixin,
    Base,
):
    """An individual failure observed during a search execution."""

    __tablename__ = "processing_failures"

    __table_args__ = (
        CheckConstraint(
            "item_index >= 0",
            name="nonnegative_item_index",
        ),
        CheckConstraint(
            "length(btrim(stage)) > 0",
            name="nonempty_stage",
        ),
        CheckConstraint(
            "length(btrim(message)) > 0",
            name="nonempty_message",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("search_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    business_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        index=True,
    )

    item_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stage: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    item_name: Mapped[str | None] = mapped_column(Text)

    job: Mapped[SearchJobRecord] = relationship(
        back_populates="failures",
        lazy="raise",
    )
