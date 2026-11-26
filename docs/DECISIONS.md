
# Business Lead Intelligence — Architectural Decisions

Last updated: 26 November 2026

## Decision Status

- Accepted: Approved architectural direction.
- Proposed: Requires further review.
- Deferred: Intentionally postponed.
- Superseded: Replaced by a later decision.

---

## ADR-001: Backend-First Development

Status: Accepted

Decision:
Develop and stabilize the Python backend before building
the frontend and production infrastructure.

Reason:
The discovery pipeline is the core functionality of the
application. Building the frontend prematurely would
increase coupling and unnecessary rework.

Consequences:
- Backend correctness receives priority.
- Frontend development begins after stabilization.
- Core business logic remains independently testable.

## ADR-002: Python as the Core Backend Language

Status: Accepted

Decision:
Use Python for business discovery, scraping, extraction,
normalization, processing, and backend API development.

Reason:
Python provides suitable libraries for HTTP communication,
HTML processing, data validation, testing, and automation.

## ADR-003: Serper as the Initial Search Provider

Status: Accepted

Decision:
Use Serper Places and Resolve APIs for business discovery
and supported redirect resolution.

Reason:
A managed search provider reduces the complexity of
maintaining direct search engine scraping.

Consequences:
- External API costs must be monitored.
- Rate limits must be respected.
- Responses must be validated.
- Provider-specific logic must remain isolated.
- Additional providers may be introduced later.

## ADR-004: HTTP-Based Website Scraping

Status: Accepted

Decision:
Use Requests and BeautifulSoup for initial website
retrieval and HTML processing.

Reason:
HTTP-based scraping is simpler and generally requires
fewer resources than browser automation.

Consequences:
- JavaScript-dependent websites may have incomplete results.
- Browser automation remains an optional improvement.
- External requests require strict security controls.

## ADR-005: Modular Backend Architecture

Status: Accepted

Decision:
Separate search providers, models, mapping, extraction,
scraping, services, exporters, and utilities.

Reason:
Separation of concerns improves maintainability,
testability, and future integration with FastAPI.

## ADR-006: International Business Discovery

Status: Accepted

Decision:
Design the platform for international business discovery
rather than restricting it to Nepal.

Reason:
The company requires international business contacts
and potential partnerships.

Consequences:
- Country context must be configurable.
- Phone normalization must support international regions.
- Geographic information must not be fabricated.
- Hardcoded geographical assumptions must be reviewed.

## ADR-007: Rule-Based Lead Scoring

Status: Accepted

Decision:
Use deterministic rules for the initial lead scoring system.

Reason:
Rule-based scoring is transparent, inexpensive,
testable, and sufficient for the initial requirements.

Consequences:
- Scores represent information completeness.
- Scores do not independently verify business legitimacy.
- Machine learning is not required for initial deployment.

## ADR-008: Excel and CSV Export

Status: Accepted

Decision:
Support Excel and CSV as the initial export formats.

Reason:
Both formats are suitable for company workflows and
further business data processing.

Consequences:
- Export fields should remain consistent.
- International characters must be supported.
- Formula injection protection is mandatory.

## ADR-009: Automated Testing and Continuous Integration

Status: Accepted

Decision:
Use pytest, Ruff, and GitHub Actions for automated
development verification.

Reason:
Automated verification reduces regressions and improves
confidence in implementation changes.

Consequences:
- External services must be mocked in ordinary tests.
- Tests must not consume paid API credits.
- Code changes require appropriate verification.
- Failed CI checks must be investigated.

## ADR-010: FastAPI for the Application API

Status: Accepted — Implementation Pending

Decision:
Use FastAPI to expose application functionality through
a structured HTTP API.

Reason:
FastAPI supports Python type hints, request validation,
dependency injection, and automatic API documentation.

Consequences:
- Existing business logic must remain reusable.
- API handlers must not directly perform long-running
  scraping operations.

## ADR-011: React for the Frontend

Status: Accepted — Implementation Pending

Decision:
Use React for the employee-facing web application.

Reason:
React supports reusable interface components and
integration with a separate backend API.

Consequences:
- Core business logic remains in Python.
- Frontend implementation follows backend stabilization.
- The initial interface should remain simple.

## ADR-012: Persistent Relational Database

Status: Accepted — Technology Selection Pending

Decision:
Store businesses, contacts, search history, users,
and processing jobs in a relational database.

Reason:
The application requires persistent records,
relationships, filtering, and data consistency.

Consequences:
- Database migrations will be required.
- Uniqueness constraints must be designed carefully.
- Database transactions must preserve consistency.

The database engine and access strategy remain undecided.

## ADR-013: Background Job Processing

Status: Accepted — Technology Selection Pending

Decision:
Execute long-running business discovery operations
through background jobs.

Reason:
Search and website extraction operations may take longer
than an ordinary HTTP request should remain open.

Consequences:
- Jobs require persistent status and progress information.
- Worker failures must be handled.
- Shared API rate limits must be enforced.
- Queue technology remains undecided.

## ADR-014: Controlled Concurrency

Status: Deferred

Decision:
Postpone concurrent website extraction until the
sequential backend is sufficiently stable.

Reason:
Concurrency introduces additional resource management,
rate limiting, synchronization, and testing complexity.

Revisit when:
- Backend stabilization is complete.
- Performance bottlenecks have been measured.
- Appropriate concurrency limits have been designed.

## ADR-015: Playwright Browser Automation

Status: Deferred

Decision:
Do not introduce Playwright during initial backend
stabilization.

Reason:
Browser automation increases memory consumption,
execution complexity, deployment requirements,
and network security concerns.

Revisit when:
- HTTP-based extraction limitations have been measured.
- Browser automation provides a justified improvement.
- Appropriate security controls can be implemented.

## ADR-016: Duplicate Search Detection

Status: Accepted — Implementation Pending

Decision:
Store normalized search identities based on country,
city, and business query.

Reason:
Repeated searches may consume unnecessary API credits
and duplicate existing business data.

Consequences:
- Users must be informed about existing results.
- Explicit re-fetching must remain available.
- Requested result limits and previous job outcomes
  must be considered when reusing results.

## ADR-017: Repository as the Source of Truth

Status: Accepted

Decision:
Maintain project requirements, engineering instructions,
architecture, roadmap, status, and decisions in Git.

Reason:
Development must remain recoverable without relying
exclusively on AI conversation history.

Consequences:
- Documentation must reflect verified implementation.
- Significant decisions must be recorded.
- Outdated documentation must be corrected.

---

## Pending Technical Decisions

The following require further evaluation:

- Database engine
- ORM and migration tooling
- Background job queue
- Authentication mechanism
- Session management
- Hosting provider
- Deployment infrastructure
- Containerization strategy
- International address normalization
- Business branch identity
- Concurrency limits
- Logging and monitoring infrastructure
- Data retention policy
- API consumption budgets

Do not treat pending decisions as approved technologies.

## Decision Maintenance

When introducing a significant architectural decision,
record:

- Decision identifier
- Title
- Status
- Context
- Decision
- Reason
- Consequences

Do not silently replace accepted decisions.
Record the replacement and mark the previous
decision as superseded where appropriate.
