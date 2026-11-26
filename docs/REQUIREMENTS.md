
# Business Lead Intelligence — Requirements

## 1. Purpose

This document defines the target functional and
non-functional requirements of the platform.

A requirement being listed does not indicate that it
has already been implemented.

Implementation progress is tracked separately in
docs/ROADMAP.md and docs/PROJECT_STATUS.md.

## 2. Functional Requirements

### FR-01: Authentication

- Users must authenticate before accessing the application.
- Unauthorized users must not access business data.
- The application must support multiple authorized employees.
- Passwords must never be stored in plaintext.
- Users must be able to log out securely.

### FR-02: Search Input

The application must accept:

- Country selection
- City or target location
- Business search query
- Maximum requested results

Inputs must be validated before executing searches.

The initial maximum result limit is 100 per search,
subject to provider capabilities and cost controls.

Country selection must support standardized country codes.

### FR-03: Business Discovery

- Discover businesses using the configured search provider.
- Support international search queries.
- Support result pagination where available.
- Respect the requested maximum result count.
- Handle empty search results.
- Validate external API responses.
- Handle malformed responses and invalid JSON.
- Handle recoverable external service failures.
- Prevent unnecessary external API requests.

The initial search provider is Serper Places.

### FR-04: Website Resolution

- Resolve supported search-provider redirect URLs.
- Normalize website URLs.
- Validate website URLs.
- Prefer official business websites.
- Reject unsafe URLs.
- Avoid treating unrelated third-party listings as
  official business websites.
- Preserve businesses that do not have an available website.

### FR-05: Business Data Mapping

Map external provider results into a consistent internal
business representation.

The target business record must support:

| Field | Description |
|---|---|
| Business ID | Internal persistent identifier |
| Name | Business name |
| Address | Available business address |
| City | Business city, when known |
| District | Business district, when known |
| State or Province | Administrative region |
| Country | Business country, when known |
| Country Code | Standardized country code |
| Category | Business category |
| Website | Validated business website |
| Emails | Collection of available email addresses |
| Phone Numbers | Collection of available phone numbers |
| Source URLs | Origins of collected information |
| Contact Page URLs | Discovered contact-related pages |
| Extraction Status | Contact extraction outcome |
| Lead Score | Rule-based completeness score |
| Lead Quality | Derived quality classification |
| Created At | Record creation timestamp |
| Updated At | Last record update timestamp |

Geographical values requested by the user must not
automatically be treated as verified business locations.

Missing information must remain explicitly unknown.

### FR-06: Contact Discovery

- Visit validated business websites.
- Extract relevant business email addresses.
- Extract relevant business phone numbers.
- Discover contact-related pages.
- Discover relevant about pages.
- Avoid processing unnecessary pages.
- Deduplicate discovered contact information.
- Record useful source information.
- Preserve available search-provider contact information.
- Continue processing other businesses when one website fails.

### FR-07: Contact Normalization

- Normalize email addresses consistently.
- Validate email address syntax.
- Normalize supported phone numbers into E.164 format.
- Use appropriate country or region context for local numbers.
- Support international phone numbers.
- Reject invalid contact values where appropriate.

Email syntax validation does not guarantee that an
email address exists or can receive messages.

### FR-08: Business Deduplication

Identify potential duplicate businesses using appropriate
combinations of:

- Normalized website identity
- Normalized phone numbers
- Business name
- Business address
- Geographic context

The application must:

- Avoid inserting unnecessary duplicate records.
- Merge compatible information where appropriate.
- Preserve valid previously collected contact information.
- Avoid incorrectly merging unrelated businesses.
- Account for businesses with multiple branches.

Matching rules must be documented and tested.

### FR-09: Lead Scoring

- Calculate a deterministic lead score.
- Derive a lead quality classification.
- Handle incomplete business records.
- Keep scoring rules documented and testable.

Initial scoring rules:

| Criterion | Points |
|---|---:|
| Available email | 30 |
| Available phone number | 20 |
| Available website | 15 |
| Available address | 10 |
| Available category | 10 |
| At least two contact methods | 15 |

Maximum score: 100

Initial classifications:

- High: 80–100
- Medium: 50–79
- Low: 0–49

A high lead score indicates information completeness,
not independently verified business legitimacy,
commercial value, or contact deliverability.

Scoring rules must be verified against the implementation
during the backend audit.

### FR-10: Duplicate Search Detection

- Store previously executed search parameters.
- Normalize search parameters consistently.
- Detect duplicate search requests.
- Inform users when matching previous results exist.
- Allow users to explicitly request a new search.
- Avoid unnecessary paid API usage.

The initial logical query identity consists of:

- Country
- City
- Search query

Other parameters, including maximum result count,
must be considered when deciding whether previous
results satisfy a new request.

### FR-11: Persistent Storage

- Store collected businesses in a database.
- Store contact information and source information.
- Store search history.
- Store discovery job information.
- Preserve previously collected businesses.
- Support updating existing records.
- Prevent unnecessary duplicate records.
- Support retrieval by country and city.
- Use database migrations for schema changes.

Different searches may discover the same business.

The persistence model must preserve relationships
between businesses and their discovery searches.

### FR-12: Background Job Processing

- Execute discovery jobs independently of the browser request.
- Allow users to retrieve job status.
- Report meaningful processing progress.
- Handle partial failures.
- Preserve useful error information.
- Prevent jobs from remaining indefinitely in a running state.
- Respect shared provider rate limits.
- Prevent uncontrolled concurrent execution.

Proposed job states:

- Queued
- Running
- Completed
- Partially completed
- Failed
- Cancelled

Cancellation behavior requires further design.

### FR-13: Export

Support:

- Excel (.xlsx)
- CSV (.csv)

The application must:

- Export stored businesses by country and city.
- Include available required business fields.
- Handle missing values consistently.
- Support international characters.
- Prevent spreadsheet formula injection.
- Generate readable and valid output files.
- Prevent unauthorized access to exported data.
- Avoid exposing unrelated internal configuration.

Excel and CSV export field definitions must be
reviewed for consistency.

### FR-14: Frontend

Provide a React-based interface with:

- Login page
- Business extraction page
- Country selector
- City input
- Business query input
- Maximum results input
- Duplicate query notification
- Job status and progress information
- Export page
- Country and city export filters
- Excel download action
- CSV download action

The initial interface does not require a complete
interactive business management dashboard.

### FR-15: Error Reporting

- Display understandable errors to users.
- Preserve technical error details in controlled logs.
- Distinguish between complete and partial failures.
- Avoid exposing secrets or internal stack traces to users.
- Record failed extraction stages where appropriate.

## 3. Non-Functional Requirements

### NFR-01: Security

Protect against:

- Server-side request forgery
- DNS rebinding
- Unsafe redirects
- SQL injection
- Spreadsheet formula injection
- Unauthorized access
- Credential exposure
- Resource exhaustion
- Excessive external requests

Production traffic must use HTTPS.

Security requirements apply to both initial implementation
and subsequent improvements.

### NFR-02: Reliability

- Individual website failures must not unnecessarily
  terminate entire discovery jobs.
- External requests must have bounded timeouts.
- Retry behavior must be bounded.
- External responses must be validated.
- Managed resources must be released appropriately.
- Database writes must preserve data consistency.

### NFR-03: Performance

- Avoid unnecessary HTTP requests.
- Avoid unbounded scraping.
- Avoid unnecessary API calls.
- Use appropriate response-size limits.
- Support background processing.
- Introduce bounded concurrency after backend stabilization.

Performance targets must be measured using realistic
workloads before production release.

### NFR-04: Scalability

- Support approximately 3–4 employees initially.
- Allow controlled growth in users and stored businesses.
- Avoid tightly coupling business logic to the frontend.
- Avoid tightly coupling core business logic to a
  particular external provider.
- Enforce shared rate and resource limits.

### NFR-05: Maintainability

- Maintain modular components.
- Follow consistent coding standards.
- Use descriptive names and appropriate type hints.
- Document significant architectural decisions.
- Avoid unnecessary dependencies.
- Maintain automated tests.
- Maintain a comprehensive development roadmap.

### NFR-06: Testability

- Use pytest.
- Test normal and exceptional behavior.
- Mock external services in automated tests.
- Test malformed input and external responses.
- Include regression tests for confirmed defects.
- Run automated checks through GitHub Actions.
- Do not consume paid API credits in ordinary CI runs.

### NFR-07: Observability

- Maintain structured operational logs.
- Record job failures.
- Track processing durations.
- Track external API usage.
- Track useful extraction success and failure metrics.
- Avoid logging credentials and unnecessary personal data.

### NFR-08: Cost Control

- Respect Serper API usage limits.
- Avoid unnecessary duplicate requests.
- Track provider consumption.
- Use bounded retry policies.
- Restrict maximum search results.
- Introduce configurable usage limits before deployment.

### NFR-09: Data Privacy

- Collect only necessary business information.
- Respect applicable laws and access restrictions.
- Restrict data access to authorized users.
- Avoid unnecessary collection of sensitive personal data.
- Define retention and deletion procedures before deployment.

### NFR-10: Deployment and Recovery

- Separate development and production configuration.
- Manage secrets securely.
- Support repeatable deployment.
- Maintain database backups.
- Establish tested recovery procedures.
- Provide health checks and operational documentation.

### NFR-11: Usability

- Employees must be able to use the platform without
  developer assistance.
- Inputs must have understandable validation messages.
- Job progress must be understandable.
- Export operations must be straightforward.
- User-facing failures must provide useful next steps.

## 4. Production Acceptance Criteria

Before production release:

- Core backend requirements must be implemented and verified.
- Required security controls must be tested.
- International business discovery must be tested.
- Persistence and deduplication must be verified.
- Authentication and authorization must be verified.
- Background job failure handling must be tested.
- Excel and CSV output must be validated.
- End-to-end application workflows must pass testing.
- Production deployment must use secure configuration.
- Backup and recovery procedures must be tested.
- Company stakeholders must accept the release.

## 5. Open Technical Decisions

The following require architectural review:

- Database technology
- ORM and migration tooling
- Background job infrastructure
- Authentication implementation
- Hosting provider
- International address normalization
- Business branch identity
- Extraction concurrency limits
- Browser automation fallback
- Data retention policy
- Monitoring infrastructure
- Performance acceptance thresholds
- API usage budgets

Record approved decisions in docs/DECISIONS.md.

## 6. Requirement Change Management

Requirements may evolve during development.

Significant requirement changes must be reflected in:

- docs/REQUIREMENTS.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/DECISIONS.md

Do not introduce major features without evaluating
their impact on security, cost, architecture, and
project delivery.
