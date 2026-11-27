"""Read-only preview for a single existing search job. No provider calls."""

import argparse
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.models import BusinessRecord, SearchResultRecord
from src.lead_intelligence.database.settings import DatabaseSettings
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.geographic_enrichment import (
    GeographicEnrichmentService,
)

FIELDS = ("city", "district", "state", "country", "country_code")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", type=UUID, required=True)
    args = parser.parse_args()
    engine = create_database_engine(DatabaseSettings.load(Path(".env")))
    try:
        with Session(engine) as session:
            records = session.scalars(
                select(BusinessRecord)
                .join(
                    SearchResultRecord,
                    SearchResultRecord.business_id == BusinessRecord.id,
                )
                .where(SearchResultRecord.job_id == args.job_id)
                .order_by(SearchResultRecord.position)
            ).all()
            service = GeographicEnrichmentService()
            for record in records:
                before = {field: getattr(record, field) for field in FIELDS}
                candidate = Business(
                    name=record.name,
                    address=record.address,
                    latitude=record.latitude,
                    longitude=record.longitude,
                    geographic_sources=record.geographic_sources,
                    geographic_conflicts=record.geographic_conflicts,
                    **before,
                )
                service.enrich(candidate)
                print(
                    json.dumps(
                        {
                            "id": str(record.id),
                            "name": record.name,
                            "before": before,
                            "proposed": {
                                field: getattr(candidate, field) for field in FIELDS
                            },
                            "geographic_sources": candidate.geographic_sources,
                            "geographic_conflicts": candidate.geographic_conflicts,
                        },
                        ensure_ascii=True,
                        indent=2,
                    )
                )
            print(f"Previewed {len(records)} businesses; no records modified.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
