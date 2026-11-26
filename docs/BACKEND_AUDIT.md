
# Business Lead Intelligence — Backend Audit

Last updated: 26 November 2026

## 1. Audit Objective

Evaluate the existing Python backend for correctness,
security, reliability, maintainability, testability,
and alignment with production requirements.

The backend must be sufficiently stable before database,
API, frontend, and concurrency development.

## 2. Audit Status

- Baseline commit: d167788
- Audit status: Local stabilization verified; final commit/CI pending
- Production readiness: Not established
- Confirmed findings and residual risks recorded below

## 3. Severity Classification

| Severity | Description |
|---|---|
| Critical | Serious security or data integrity risk |
| High | Major reliability or correctness problem |
| Medium | Significant quality or maintainability issue |
| Low | Minor defect or improvement opportunity |
| Informational | Observation without an immediate defect |

## 4. Finding Status

- Unverified: Requires investigation.
- Confirmed: Defect established through evidence.
- In progress: Resolution underway.
- Resolved: Fix implemented and verified.
- Deferred: Resolution intentionally postponed.
- Not applicable: Investigation found no relevant issue.

## 5. Audit Queue

| ID | Component | Investigation | Status |
|---|---|---|---|
| AUD-001 | Engineering | Automated test baseline | Verified locally |
| AUD-002 | Engineering | Dependency management | Resolved locally; lock deferred |
| AUD-003 | Engineering | CI configuration | Configured; final CI pending |
| AUD-004 | Architecture | Component responsibilities | Core reviewed; infrastructure pending |
| AUD-005 | Business model | Missing required fields | Core model verified; persistent fields pending |
| AUD-006 | Business mapper | Geographic data handling | Offline verified; geocoding deferred |
| AUD-007 | Serper provider | Request validation | Verified locally; residual risks below |
| AUD-008 | Serper provider | Response validation | Verified locally; residual risks below |
| AUD-009 | Serper provider | Retry and rate limiting | Verified locally; residual risks below |
| AUD-010 | Business search | Pagination and termination | Verified locally; residual risks below |
| AUD-011 | Business search | Duplicate results | Verified locally; residual risks below |
| AUD-012 | URL security | SSRF protection | Verified locally; residual risks below |
| AUD-013 | URL security | DNS rebinding protection | Verified locally; residual risks below |
| AUD-014 | Website scraper | Redirect validation | Verified locally; residual risks below |
| AUD-015 | Website scraper | Response-size limits | Verified locally; residual risks below |
| AUD-016 | Website scraper | Timeout and cleanup | Verified locally; residual risks below |
| AUD-017 | Contact discovery | Contact page selection | Improved; ranking deferred |
| AUD-018 | Contact discovery | Source tracking | Verified locally; residual risks below |
| AUD-019 | Contact discovery | Partial failure handling | Verified locally; residual risks below |
| AUD-020 | Contact extraction | Email extraction accuracy | Syntax/extraction verified; relevance deferred |
| AUD-021 | Contact extraction | Phone normalization | Verified locally; residual risks below |
| AUD-022 | Deduplication | Incorrect business merging | Verified locally; residual risks below |
| AUD-023 | Deduplication | Multiple business branches | CID rules verified; persistent identity pending |
| AUD-024 | Lead scoring | Score and quality correctness | Verified locally; residual risks below |
| AUD-025 | Excel exporter | Formula injection protection | Verified locally; residual risks below |
| AUD-026 | CSV exporter | Formula injection protection | Verified locally; residual risks below |
| AUD-027 | Exporters | Field consistency | Shared schema verified; live CSV parity pending |
| AUD-028 | CLI | Hardcoded geographic assumptions | Verified locally; residual risks below |
| AUD-029 | CLI | Pipeline orchestration coupling | Verified locally; residual risks below |
| AUD-030 | Configuration | Secret management | Local scans passed; production secrets pending |
| AUD-031 | Testing | Missing regression coverage | Local acceptance passed; final CI pending |
| AUD-032 | Testing | Pytest asyncio warning | Resolved locally |

| AUD-033 | Website acquisition | Optional fallback and diagnostics | Locally verified; live recovery effectiveness unproven |

The audit queue identifies investigation targets.
It does not establish that these components are defective.

## 6. Confirmed Findings


### FIND-001: Mixed and Unpinned Direct Dependencies

- Audit reference: AUD-002
- Severity: Medium
- Status: Resolved locally; remote CI verification pending
- Affected files:
  - requirements.txt
  - requirements-dev.txt
  - .github/workflows/ci.yml
  - README.md
- Related requirements: NFR-05, NFR-06, NFR-10

#### Description

Runtime and development dependencies were combined
in a single requirements file without version pinning.

Several declared packages were not required by the
current implementation.

#### Resolution

- Separated runtime and development dependencies.
- Pinned direct dependency versions.
- Removed seven unnecessary direct dependencies.
- Reduced direct dependencies from 20 to 13.
- Updated CI to install development requirements.
- Enabled pip caching in CI.
- Added dependency compatibility checks.

#### Verification

Verified using an isolated Python 3.13.17 environment.

- Dependency installation: Passed
- Pip check: Passed
- Pytest: 202 passed in 7.17 seconds
- Ruff linting: Passed
- Ruff formatting: 48 files correctly formatted
- Pytest asyncio warning: No longer present

#### Remaining Work

- Final checkpoint remote CI verification
- Transitive dependency locking (both local vulnerability scans passed)


### Additional verified findings and fixes (Day 4)

| Audit references | Evidence / resolution | Residual risk |
|---|---|---|
| AUD-005–011, 028 | Structured requests, bounded pagination, CID alignment, credit counters and international mapping | Provider variability; unknown billing on retries |
| AUD-012–016 | Connection-time public IP checks, TLS verification, redirects, response bounds and local security regression tests | Production egress isolation, hard deadlines and transport upgrade review |
| AUD-017–023 | HTML contact extraction, source evidence, same-site policy and branch-aware CID matching | False positives, page ranking, historical identity |
| AUD-024–027 | Versioned completeness scoring, shared schema, formula safety and atomic individual exports | Contact relevance and paired export transaction |
| AUD-029–030 | Reusable pipeline, explicit settings, redacted logging and secret scans | Shared rate limiting, structured logging and production secret management |
| AUD-031–033 | Regression suite and live acquisition diagnostics; opt-in fallback | Final CI; fallback recovery benefit unproven |

Local verification on 26 November 2026 (Python 3.13.17, Windows):

- 1,173 tests passed in 19.79 seconds; 96% statement coverage (2,012 statements, 80 missed). Coverage excludes main.py and is not branch coverage.
- pip check and Ruff lint passed; 86 Python files formatted; staged and unstaged diff checks clean.
- Both declared-dependency and installed-environment pip-audit scans reported no known vulnerabilities earlier in the session; no dependencies changed in the final acquisition batch.
- Gitleaks: 38 commits / approximately 706,801 bytes of history and 14,197 bytes of staged changes scanned; no leaks, both exit codes 0. .env ignored, untracked and absent from available history.
- Latest acquisition changes: 11 staged files, 337 insertions, 2 deletions, based on 7bc9e25. Final commit and remote CI not yet verified.

## 7. Finding Template

### FIND-XXX: Finding Title

- Audit reference:
- Severity:
- Status:
- Affected files:
- Related requirement:

#### Description

Explain the identified problem.

#### Evidence

Document relevant code, observed behavior,
or reproducible test results.

#### Impact

Explain the security, reliability, correctness,
or maintainability consequences.

#### Proposed Resolution

Describe the recommended solution.

#### Verification

Document regression tests and verification results.

#### Resolution Commit

Record the commit that resolves the finding.

## 8. Deferred Technical Debt

- Provider results vary between repeated searches. Direct/Resolve URLs are candidates, not independent ownership proof. Organic fallback is opt-in and requires homepage name and matching phone; live recovery effectiveness remains unproven. Candidate ranking and contact-page verification need improvement.
- Structured business geography remains incomplete. Search geography is not verified business geography; preserve unknown fields. Persistent reverse geocoding/cache is planned.
- Email syntax and phone validity do not establish ownership, freshness, deliverability or commercial relevance. Scores measure completeness.
- HTTP-only extraction can fail on blocked, compressed, JavaScript-dependent or non-200 responses; no bypass. Contact-page ranking and redundant redirected downloads can be improved.
- SSRF controls are locally tested, not a substitute for production network isolation. DNS/time budgets are cooperative; per-session rate limits are not shared worker limits. Review private httpcore transport integration on upgrades.
- Direct dependencies are pinned, transitive locking and automated recurring security scanning remain pending. Secret scans are not guarantees.
- Atomic export protects individual files, not the Excel/CSV pair as a transaction. Live CSV parity was not independently inspected.
- Persistent identity, historical data merging, job recovery, authentication, structured operational logging, deployment and backups remain unimplemented.

Reconsider persistence-related issues in Phase 4, extraction performance in Phase 9, and infrastructure/security risks before production in Phases 10–11.

## 9. Backend Stabilization Gate

- [x] Establish automated verification baseline.
- [x] Review core backend components within local stabilization scope.
- [x] Record confirmed findings.
- [x] Address identified local SSRF/export security findings; production review pending.
- [x] Address identified local blocking reliability issues.
- [x] Address identified local export and merge risks; persistence risks pending.
- [x] Document remaining technical debt.
- [x] Verify sampled international CLI compatibility.
- [x] Run complete automated test suite.
- [x] Pass Ruff linting and formatting.
- [x] Complete controlled live pipeline testing; fallback recovery not established.
- [ ] Pass GitHub Actions CI.
- [ ] Update project status and master roadmap.

## 10. Audit Rules

- Inspect implementation before proposing changes.
- Distinguish potential weaknesses from confirmed defects.
- Prioritize findings according to impact.
- Avoid unrelated refactoring.
- Preserve existing functionality.
- Add regression tests for confirmed defects.
- Verify fixes before closing findings.
- Maintain traceability to project requirements.
- Follow AGENTS.md.
