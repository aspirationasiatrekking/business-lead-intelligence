from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.lead_intelligence.database.exceptions import PersistenceValidationError
from src.lead_intelligence.database.mappers.business import complete_record_to_business
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    BusinessRecord,
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.exporters.csv_exporter import export_businesses_to_csv
from src.lead_intelligence.exporters.excel_exporter import export_businesses_to_excel
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.search_request import SearchRequest

MAX_EXPORT_ROWS = 10_000


def location_statement(country_code: str, city: str):
    # Reuse search input normalization, not business geography.
    request = SearchRequest(country_code=country_code, city=city, query="export")
    country, normalized_city, _ = request.signature
    ids = (
        select(SearchResultRecord.business_id)
        .join(SearchJobRecord, SearchResultRecord.job_id == SearchJobRecord.id)
        .join(SearchQueryRecord, SearchJobRecord.query_id == SearchQueryRecord.id)
        .where(
            SearchQueryRecord.country_code == country,
            SearchQueryRecord.city_normalized == normalized_city,
            SearchJobRecord.status.in_(("completed", "partial")),
        )
    )
    return (
        select(BusinessRecord)
        .where(BusinessRecord.id.in_(ids))
        .options(
            selectinload(BusinessRecord.contacts).selectinload(
                BusinessContactRecord.sources
            ),
            selectinload(BusinessRecord.sources),
        )
        .order_by(BusinessRecord.created_at, BusinessRecord.id)
        .limit(MAX_EXPORT_ROWS + 1)
    )


def load_location_businesses(
    session: Session, country_code: str, city: str
) -> list[Business]:
    records = session.scalars(location_statement(country_code, city)).all()
    if len(records) > MAX_EXPORT_ROWS:
        raise PersistenceValidationError("Location exceeds maximum export size.")
    return [complete_record_to_business(record) for record in records]


def export_location(
    session: Session,
    country_code: str,
    city: str,
    output_path: str,
    *,
    file_format: str,
) -> int:
    if file_format not in ("csv", "xlsx"):
        raise PersistenceValidationError("Unsupported export format.")
    businesses = load_location_businesses(session, country_code, city)
    exporter = (
        export_businesses_to_csv if file_format == "csv" else export_businesses_to_excel
    )
    exporter(businesses, output_path)
    return len(businesses)
