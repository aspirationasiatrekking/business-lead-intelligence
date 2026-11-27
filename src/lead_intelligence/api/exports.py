from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from sqlalchemy import distinct, func, select

from src.lead_intelligence.api.job_schemas import ErrorResponse, SearchInput
from src.lead_intelligence.api.jobs import SessionDep
from src.lead_intelligence.database.models import (
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.database.services.location_export import export_location

router = APIRouter(
    prefix="/api/v1",
    tags=["Exports"],
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


class LocationResponse(BaseModel):
    country_code: str
    city: str
    business_count: int


class LocationPage(BaseModel):
    items: list[LocationResponse]
    limit: int
    offset: int
    has_more: bool


@router.get("/locations")
def locations(
    session: SessionDep,
    country_code: Annotated[str | None, Query(max_length=16)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> LocationPage:
    statement = (
        select(
            SearchQueryRecord.country_code,
            func.min(SearchQueryRecord.city).label("city"),
            func.count(distinct(SearchResultRecord.business_id)).label(
                "business_count"
            ),
        )
        .join(SearchJobRecord, SearchJobRecord.query_id == SearchQueryRecord.id)
        .join(SearchResultRecord, SearchResultRecord.job_id == SearchJobRecord.id)
        .where(SearchJobRecord.status.in_(("completed", "partial")))
        .group_by(SearchQueryRecord.country_code, SearchQueryRecord.city_normalized)
        .order_by(SearchQueryRecord.country_code, SearchQueryRecord.city_normalized)
    )
    if country_code is not None:
        country = (
            SearchInput(country_code=country_code, city="export", query="export")
            .to_domain()
            .country_code
        )
        statement = statement.where(SearchQueryRecord.country_code == country)
    rows = session.execute(statement.offset(offset).limit(limit + 1)).all()
    return LocationPage(
        items=[
            LocationResponse(country_code=country, city=city, business_count=count)
            for country, city, count in rows[:limit]
        ],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )


@router.get(
    "/exports",
    response_class=Response,
    responses={
        200: {
            "content": {
                "text/csv": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
            "description": "Business leads download",
        }
    },
)
def download_export(
    session: SessionDep,
    country_code: Annotated[str, Query(max_length=16)],
    city: Annotated[str, Query(max_length=400)],
    file_format: Annotated[Literal["csv", "xlsx"], Query(alias="format")] = "xlsx",
) -> Response:
    request = SearchInput(
        country_code=country_code, city=city, query="export"
    ).to_domain()
    # Never use user-provided city text as a filesystem path or HTTP header.
    filename = f"leads-{request.country_code}.{file_format}"
    with TemporaryDirectory(prefix="bli-export-") as directory:
        path = Path(directory) / filename
        export_location(
            session,
            request.country_code,
            request.city,
            str(path),
            file_format=file_format,
        )
        content = path.read_bytes()
    media_type = (
        "text/csv; charset=utf-8"
        if file_format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
