# Database development checkpoint

The database layer uses PostgreSQL, SQLAlchemy and Alembic. Keep runtime
(`bli_app`) and migration (`bli_migrator`) credentials separate. Do not commit
`.env`, passwords, API keys or private certificates. Runtime credentials must
not own the schema or be used for migrations.

## Verification

From the repository root, with the development `.env` and virtual environment:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -q --cov=src/lead_intelligence --cov-report=term
python -m alembic current
python -m alembic check
python -m pip check
python -m scripts.verify_database_pipeline --development
```

Run the last command only against the disposable development database. It
checks the effective privileges of four known roles and RLS on the eight
application tables, search history, job transitions, simulated pipeline
execution, deduplication and actual CSV/XLSX exports. It uses an outer
transaction and nested savepoints, rolls back synthetic records, and verifies
cleanup on another connection. Temporary exports are removed automatically.
It does not contact Serper or crawl websites. Never point this script at
production. The flag is an explicit operator acknowledgement, not an
independent environment detector.

## Remaining release gates

- Real committed-transaction and concurrent-worker tests in an isolated database.
- Full grant/default ACL/role membership audit, including unexpected grantees.
- Dependency vulnerability and secret scanning; resolve findings before release.
- API authorization, background worker recovery, request limits, job cancellation
  semantics, operational logging and production backup/restore.
- Verify GitHub Actions after committing. Mocked tests are not a substitute for
  PostgreSQL integration tests.

The search location is distinct from verified business geography. Location
exports combine distinct canonical businesses associated with completed or
partial jobs for the requested country and city. Search results retain the
score and status at discovery, not a complete historical copy of each business.

The job runner is synchronous; persistent queue execution and recovery are
future work. Cooperating canonical business writers must use the same advisory
lock protocol. Do not expose the development database or the runner directly
as a public API.
