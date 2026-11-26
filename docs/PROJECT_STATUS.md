# Business Lead Intelligence — Project Status

Last updated: 26 November 2026 (Day 4)

## 1. Current position

Internal company project for Aspiration Asia Trekking; approximately 3–4 employees initially. Repository: https://github.com/aspirationasiatrekking/business-lead-intelligence. Branch main. Phases 0–1 established; Phase 2 local stabilization verified, final documentation/commit/CI gate pending; Phase 3 international CLI core verified with deferred enrichment. Phase 4 database design is next after checkpoint closure. Not production-ready.

## 2. Verified checkpoint

Local verification on 26 November 2026 (Python 3.13.17, Windows):

- 1,173 tests passed in 19.79 seconds; 96% statement coverage (2,012 statements, 80 missed). Coverage excludes main.py and is not branch coverage.
- pip check and Ruff lint passed; 86 Python files formatted; staged and unstaged diff checks clean.
- Both declared-dependency and installed-environment pip-audit scans reported no known vulnerabilities earlier in the session; no dependencies changed in the final acquisition batch.
- Gitleaks: 38 commits / approximately 706,801 bytes of history and 14,197 bytes of staged changes scanned; no leaks, both exit codes 0. .env ignored, untracked and absent from available history.
- Latest acquisition changes: 11 staged files, 337 insertions, 2 deletions, based on 7bc9e25. Final commit and remote CI not yet verified.

## 3. Implemented core

Structured country/city/query/limit input; paginated Serper Places/Resolve with bounded retry and credit tracking; CID and coordinate mapping, conservative geographic enrichment and identity deduplication; secure HTTP website retrieval; contact discovery and provenance; opt-in organic acquisition and diagnostics; scoring policy v2; shared 16-column Excel/CSV schema and per-file atomic exports; reusable pipeline with progress/failure reports; explicit settings and CI configuration.

## 4. Live evidence

Initial Kathmandu/London/Denver runs returned and exported 10 businesses each (30 total). Initial website counts 10/3/3, successful extraction 8/1/3. Updated London/Denver runs returned 10 each; website counts 7/5, success 5/5; reported credits 4/6, durations 86.35/74.03 s. Latest London run: 10 direct websites, zero Resolve/organic calls, one reported credit, 50.58 s, success 7, failed 1, no contacts 2; all 10 scored and exported. Repeated logs with identical run ID count as one run. These are changing provider samples, not proof of fallback effectiveness. No further paid testing required for this checkpoint.

## 5. Known limitations

- Provider results vary between repeated searches. Direct/Resolve URLs are candidates, not independent ownership proof. Organic fallback is opt-in and requires homepage name and matching phone; live recovery effectiveness remains unproven. Candidate ranking and contact-page verification need improvement.
- Structured business geography remains incomplete. Search geography is not verified business geography; preserve unknown fields. Persistent reverse geocoding/cache is planned.
- Email syntax and phone validity do not establish ownership, freshness, deliverability or commercial relevance. Scores measure completeness.
- HTTP-only extraction can fail on blocked, compressed, JavaScript-dependent or non-200 responses; no bypass. Contact-page ranking and redundant redirected downloads can be improved.
- SSRF controls are locally tested, not a substitute for production network isolation. DNS/time budgets are cooperative; per-session rate limits are not shared worker limits. Review private httpcore transport integration on upgrades.
- Direct dependencies are pinned, transitive locking and automated recurring security scanning remain pending. Secret scans are not guarantees.
- Atomic export protects individual files, not the Excel/CSV pair as a transaction. Live CSV parity was not independently inspected.
- Persistent identity, historical data merging, job recovery, authentication, structured operational logging, deployment and backups remain unimplemented.

## 6. Next tasks

1. Review and stage synchronized documentation and .env.example; scan staged changes again.
2. Commit, push and verify CI for exact new commit; record final checkpoint.
3. Phase 4: design PostgreSQL schema and identity constraints, select ORM/migrations, establish test database, implement transactional persistence and duplicate query handling, historical contact/website preservation, geographic caching and database exports.
4. Continue phases 5–12 in ROADMAP.md; design auth before exposing protected operations. No premature concurrency or Playwright.

## 7. Continuation

Read AGENTS.md, this status, ROADMAP.md, BACKEND_AUDIT.md and DEVELOPMENT_LOG.md; inspect Git state and relevant source before starting the next task. Repository evidence overrides conversation memory.
