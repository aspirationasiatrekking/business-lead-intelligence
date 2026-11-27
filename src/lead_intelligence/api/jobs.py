from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.lead_intelligence.api.auth import require_user
from src.lead_intelligence.api.dependencies import get_session
from src.lead_intelligence.api.job_schemas import (
    ErrorResponse,
    JobInput,
    JobPage,
    JobResponse,
    JobStatus,
    SearchCheckResponse,
    SearchInput,
)
from src.lead_intelligence.auth.service import Principal
from src.lead_intelligence.database.exceptions import RecordNotFoundError
from src.lead_intelligence.database.models import (
    ProcessingFailureRecord,
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.database.repositories.search import (
    ACTIVE,
    SearchRepository,
    signature_conditions,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Search jobs"],
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
SessionDep = Annotated[Session, Depends(get_session)]


def job_response(
    job: SearchJobRecord,
    query: SearchQueryRecord,
    result_count: int = 0,
    failure_count: int = 0,
) -> JobResponse:
    return JobResponse(
        id=job.id,
        query_id=query.id,
        country_code=query.country_code,
        city=query.city,
        query=query.query,
        max_results=job.max_results,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=job.duration_seconds,
        reported_credits=job.reported_credits,
        unknown_credit_responses=job.unknown_credit_responses,
        result_count=result_count,
        failure_count=failure_count,
    )


def job_statement():
    result_count = (
        select(func.count(SearchResultRecord.id))
        .where(SearchResultRecord.job_id == SearchJobRecord.id)
        .correlate(SearchJobRecord)
        .scalar_subquery()
    )
    failure_count = (
        select(func.count(ProcessingFailureRecord.id))
        .where(ProcessingFailureRecord.job_id == SearchJobRecord.id)
        .correlate(SearchJobRecord)
        .scalar_subquery()
    )
    return select(SearchJobRecord, SearchQueryRecord, result_count, failure_count).join(
        SearchQueryRecord, SearchJobRecord.query_id == SearchQueryRecord.id
    )


def newest_first(statement):
    return statement.order_by(
        SearchJobRecord.created_at.desc(), SearchJobRecord.id.desc()
    )


@router.post("/searches/check")
def check_search(body: SearchInput, session: SessionDep) -> SearchCheckResponse:
    request = body.to_domain()
    # An active job takes priority over history, even if timestamps tie.
    statement = job_statement().where(*signature_conditions(request))
    statement = newest_first(
        statement.order_by(SearchJobRecord.status.in_(ACTIVE).desc())
    ).limit(1)
    row = session.execute(statement).first()
    latest = job_response(*row) if row is not None else None
    active = latest is not None and latest.status in ACTIVE
    return SearchCheckResponse(
        exists=latest is not None,
        active_job=active,
        refetch_allowed=latest is not None and not active,
        latest_job=latest,
    )


@router.post("/jobs", status_code=202, responses={409: {"model": ErrorResponse}})
def submit_job(
    body: JobInput,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_user)],
) -> JobResponse:
    request = body.to_domain()
    # Commit before reporting acceptance; no network activity occurs here.
    with session.begin():
        job = SearchRepository(session).submit(request, refetch=body.refetch)
        job.created_by = principal.id
        parent = session.get(SearchQueryRecord, job.query_id)
        if parent is None:
            raise RecordNotFoundError("Search query not found.")
        response = job_response(job, parent)
    return response


@router.get("/jobs")
def list_jobs(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    status: JobStatus | None = None,
) -> JobPage:
    statement = job_statement()
    if status is not None:
        statement = statement.where(SearchJobRecord.status == status)
    statement = newest_first(statement).offset(offset).limit(limit + 1)
    rows = session.execute(statement).all()
    return JobPage(
        items=[job_response(*row) for row in rows[:limit]],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )


@router.get("/jobs/{job_id}", responses={404: {"model": ErrorResponse}})
def get_job(job_id: UUID, session: SessionDep) -> JobResponse:
    statement = job_statement().where(SearchJobRecord.id == job_id)
    row = session.execute(statement).one_or_none()
    if row is None:
        raise RecordNotFoundError("Search job not found.")
    return job_response(*row)
