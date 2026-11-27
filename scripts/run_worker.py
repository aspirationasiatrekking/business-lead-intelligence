"""Trusted-host worker CLI. Paid work requires an explicit execution mode."""

import argparse
import sys
from functools import partial
from pathlib import Path
from uuid import UUID

from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.services.worker import WorkerJobRunner, run_worker
from src.lead_intelligence.database.session import create_session_factory
from src.lead_intelligence.database.settings import DatabaseSettings
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.services.lead_pipeline import LeadPipelineService
from src.lead_intelligence.settings import ApplicationSettings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--job-id", type=UUID, help="Execute only this queued job")
    mode.add_argument(
        "--poll", action="store_true", help="Execute eligible queued jobs"
    )
    args = parser.parse_args()
    engine = None
    try:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        database = DatabaseSettings.load(env_file)
        if database.username.split(".", 1)[0] != "bli_app":
            raise RuntimeError("Invalid runtime database role.")
        if database.pool_size + database.max_overflow < 2:
            raise ValueError("Worker requires two available database connections.")
        settings = ApplicationSettings.load(env_file)
        if not settings.serper_api_key or settings.serper_rps != 1:
            raise ValueError("Worker requires a Serper key and a one-RPS limit.")
        pipeline = LeadPipelineService(
            search_factory=partial(BusinessSearchService, settings=settings),
            contact_service=ContactDiscoveryService(settings=settings),
        )
        engine = create_database_engine(database)
        runner = WorkerJobRunner(create_session_factory(engine), pipeline=pipeline)
        run_worker(engine, runner, job_id=args.job_id)
        return 0
    except KeyboardInterrupt:
        print(
            "Worker interrupted. Check job status before restarting.", file=sys.stderr
        )
        return 130
    except Exception as exc:
        # No SQL parameters, provider responses, credentials or raw traceback.
        print(
            f"Worker stopped ({type(exc).__name__}). Check job status before retrying.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
