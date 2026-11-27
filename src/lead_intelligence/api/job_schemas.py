from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.lead_intelligence.database.exceptions import PersistenceValidationError
from src.lead_intelligence.database.validation import validate_search_signature
from src.lead_intelligence.models.search_request import SearchRequest

JobStatus = Literal["queued", "running", "completed", "partial", "failed", "cancelled"]


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    country_code: str = Field(max_length=16)
    city: str = Field(max_length=400)
    query: str = Field(max_length=1000)
    max_results: int = Field(default=10, ge=1, le=100)

    def to_domain(self) -> SearchRequest:
        try:
            request = SearchRequest(
                country_code=self.country_code,
                city=self.city,
                query=self.query,
                max_results=self.max_results,
            )
            validate_search_signature(request)
        except (TypeError, ValueError) as exc:
            raise PersistenceValidationError("Invalid search request.") from exc
        return request


class JobInput(SearchInput):
    refetch: bool = False


class JobResponse(BaseModel):
    id: UUID
    query_id: UUID
    country_code: str
    city: str
    query: str
    max_results: int
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    reported_credits: int
    unknown_credit_responses: int
    result_count: int
    failure_count: int


class SearchCheckResponse(BaseModel):
    exists: bool
    active_job: bool
    refetch_allowed: bool
    latest_job: JobResponse | None


class JobPage(BaseModel):
    items: list[JobResponse]
    limit: int
    offset: int
    has_more: bool


class ErrorResponse(BaseModel):
    code: str
    message: str
