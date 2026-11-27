"""Opt-in development database smoke test. No paid provider requests."""

import argparse
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from openpyxl import load_workbook
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.exceptions import PersistenceConflictError
from src.lead_intelligence.database.models import (
    BusinessRecord,
    ProcessingFailureRecord,
    SearchJobRecord,
    SearchQueryRecord,
    SearchResultRecord,
)
from src.lead_intelligence.database.repositories.search import SearchRepository
from src.lead_intelligence.database.services.job_runner import DatabaseJobRunner
from src.lead_intelligence.database.services.location_export import export_location
from src.lead_intelligence.database.settings import DatabaseSettings
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.pipeline_result import PipelineResult
from src.lead_intelligence.models.processing_result import (
    ProcessingFailure,
    SearchResult,
)
from src.lead_intelligence.models.search_request import SearchRequest
from src.lead_intelligence.services.lead_scoring import LeadScoringService

TABLES = (
    "businesses",
    "business_contacts",
    "business_sources",
    "contact_sources",
    "search_queries",
    "search_jobs",
    "search_results",
    "processing_failures",
)


def verify_permissions(connection):
    assert connection.scalar(text("SELECT current_user")) == "bli_app"
    assert not connection.scalar(
        text("SELECT pg_has_role(current_user, 'bli_migrator', 'MEMBER')")
    )
    assert not connection.scalar(
        text("SELECT has_schema_privilege(current_user, 'lead_intelligence', 'CREATE')")
    )
    privilege = text(
        "SELECT has_table_privilege(CAST(:role AS text), "
        "CAST(:relation AS text), CAST(:privilege AS text))"
    )
    for table in (*TABLES, "alembic_version"):
        relation = f"lead_intelligence.{table}"
        if table in TABLES:
            assert connection.scalar(
                text(
                    "SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:name)"
                ),
                {"name": relation},
            )
        for role in ("bli_app", "anon", "authenticated", "service_role"):
            for action in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "TRUNCATE",
                "REFERENCES",
                "TRIGGER",
            ):
                expected = (
                    role == "bli_app"
                    and table in TABLES
                    and action in ("SELECT", "INSERT", "UPDATE")
                )
                actual = connection.scalar(
                    privilege,
                    {"role": role, "relation": relation, "privilege": action},
                )
                assert actual == expected, (role, relation, action)
    print("PASS: runtime permissions and application-table RLS")


class SimulatedPipeline:
    def __init__(self, marker):
        self.marker = marker

    def run(self, request):
        if request.query == "simulated failure":
            raise RuntimeError("Simulated provider failure")
        website = f"https://bli-{self.marker}.example.com"
        second = request.query == "second query"
        businesses = [
            Business(
                name=f"BLI {self.marker} A",
                website=website,
                address=f"Synthetic address {self.marker}",
                emails=["sales@example.com" if second else "info@example.com"],
                extraction_status=ExtractionStatus.SUCCESS,
            )
        ]
        if second:
            businesses.append(
                Business(
                    name=f"BLI {self.marker} B",
                    website=f"https://other-{self.marker}.example.com",
                    extraction_status=ExtractionStatus.SUCCESS,
                )
            )
        for business in businesses:
            LeadScoringService().evaluate_business(
                business, region=request.phone_region
            )
        failures = [ProcessingFailure(0, "test", "Synthetic failure")] if second else []
        return PipelineResult(
            request=request,
            search_result=SearchResult(
                request=request,
                businesses=businesses,
                total_discovered=len(businesses),
                total_mapped=len(businesses),
                pages_requested=1,
                pages_processed=1,
                reported_credits=2,
            ),
            businesses=businesses,
            failures=failures,
        )


def submit(factory, request, *, refetch=False):
    with factory.begin() as session:
        return SearchRepository(session).submit(request, refetch=refetch).id


def reject_submission(factory, request, *, refetch=False):
    try:
        submit(factory, request, refetch=refetch)
    except PersistenceConflictError:
        return
    raise AssertionError("Duplicate submission was not rejected")


def verify_flow(factory, marker):
    city = f"BLI test {marker}"
    first = SearchRequest(country_code="NP", city=city, query="first query")
    second = SearchRequest(country_code="NP", city=city, query="second query")
    runner = DatabaseJobRunner(factory, SimulatedPipeline(marker))
    first_id = submit(factory, first)
    reject_submission(factory, first, refetch=True)
    assert runner.run(first_id) == "completed"
    reject_submission(factory, first)
    second_id = submit(factory, second)
    assert runner.run(second_id) == "partial"
    refetch_id = submit(factory, first, refetch=True)
    with factory.begin() as session:
        SearchRepository(session).finish(refetch_id, "cancelled")
    failed_request = SearchRequest(
        country_code="NP", city=city, query="simulated failure"
    )
    failed_id = submit(factory, failed_request)
    try:
        runner.run(failed_id)
    except RuntimeError as error:
        assert str(error) == "Simulated provider failure"
    else:
        raise AssertionError("Simulated failure did not propagate")
    print("PASS: duplicate submission, refetch, and job transitions")

    with factory.begin() as session:
        first_job = session.get(SearchJobRecord, first_id)
        second_job = session.get(SearchJobRecord, second_id)
        failed_job = session.get(SearchJobRecord, failed_id)
        cancelled_job = session.get(SearchJobRecord, refetch_id)
        assert first_job.status == "completed" and second_job.status == "partial"
        assert failed_job.status == "failed" and cancelled_job.status == "cancelled"
        assert cancelled_job.query_id == first_job.query_id
        assert first_job.reported_credits == second_job.reported_credits == 2
        assert second_job.search_metrics["unique_persisted"] == 2
        associations = session.scalars(
            select(SearchResultRecord).where(
                SearchResultRecord.job_id.in_(
                    [first_id, second_id, failed_id, refetch_id]
                )
            )
        ).all()
        assert len(associations) == 3
        assert len({row.business_id for row in associations}) == 2
        assert all(row.lead_score_at_discovery is not None for row in associations)
        failures = session.scalars(
            select(ProcessingFailureRecord).where(
                ProcessingFailureRecord.job_id.in_([second_id, failed_id])
            )
        ).all()
        assert len(failures) == 2
        print("PASS: search history, canonical results, failures and credit accounting")

        with TemporaryDirectory(prefix="bli-smoke-") as folder:
            csv_path = Path(folder) / "leads.csv"
            xlsx_path = Path(folder) / "leads.xlsx"
            assert (
                export_location(session, "NP", city, str(csv_path), file_format="csv")
                == 2
            )
            assert (
                export_location(session, "NP", city, str(xlsx_path), file_format="xlsx")
                == 2
            )
            with csv_path.open(encoding="utf-8-sig", newline="") as file:
                csv_rows = list(csv.reader(file))
            workbook = load_workbook(xlsx_path, read_only=True)
            try:
                excel_rows = list(workbook.active.values)
            finally:
                workbook.close()
            names = {f"BLI {marker} A", f"BLI {marker} B"}
            for rows in (csv_rows, excel_rows):
                assert len(rows) == 3
                assert rows[0][0] == "Business Name"
                assert {row[0] for row in rows[1:]} == names
                merged = next(row for row in rows[1:] if row[0] == f"BLI {marker} A")
                assert "info@example.com" in merged[2]
                assert "sales@example.com" in merged[2]
        print("PASS: unique requested-location CSV and Excel exports")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", action="store_true", required=True)
    parser.parse_args()
    if not __debug__:
        raise RuntimeError("Run without Python optimization; assertions are required.")
    marker = uuid4().hex
    engine = create_database_engine(DatabaseSettings.load(Path(".env")))
    try:
        with engine.connect() as connection:
            verify_permissions(connection)
            connection.rollback()
            outer = connection.begin()
            try:
                factory = sessionmaker(
                    bind=connection,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                verify_flow(factory, marker)
            finally:
                outer.rollback()
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(SearchQueryRecord)
                    .where(SearchQueryRecord.city == f"BLI test {marker}")
                )
                == 0
            )
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(BusinessRecord)
                    .where(
                        BusinessRecord.name.in_([f"BLI {marker} A", f"BLI {marker} B"])
                    )
                )
                == 0
            )
        print("PASS: rollback and independent cleanup verification")
        print("ALL DATABASE PIPELINE SMOKE CHECKS PASSED")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
