
# Business Lead Intelligence — Master Development Roadmap

Last updated: 26 November 2026

## Status Legend

- [x] Implemented or completed at the recorded checkpoint
- [ ] Pending implementation or verification

An implemented feature is not necessarily production-ready.
Existing features must be reviewed during the backend audit.

---

## Phase 0 — Permanent Project Documentation

- [x] DOC-01: Repository inspection
- [x] DOC-02: Engineering instructions
- [x] DOC-03: Project context and requirements
- [x] DOC-04: System architecture
- [x] DOC-05: Master roadmap
- [x] DOC-06: Project status
- [x] DOC-07: Architectural decisions
- [x] DOC-08: Development and backend audit logs
- [x] DOC-09: Initial documentation review and commit (530ecd8)

Exit criteria:
- Repository contains sufficient documentation to resume
  development without relying on conversation history.

---

## Phase 1 — Backend Core Implementation

### 1.1 Engineering Foundation

- [x] Initialize Git repository
- [x] Configure Python virtual environment
- [x] Establish modular project structure
- [x] Configure environment variables
- [x] Create .env.example
- [x] Configure .gitignore
- [x] Establish dependency management
- [x] Configure pytest
- [x] Configure Ruff
- [x] Configure GitHub Actions CI

### 1.2 Search Provider

- [x] Integrate Serper Places API
- [x] Integrate Serper Resolve API
- [x] Configure request timeouts
- [x] Implement request rate limiting
- [x] Implement bounded retry policies
- [x] Implement Retry-After handling
- [x] Implement network resource cleanup
- [x] Validate Places response structure
- [x] Validate Resolve response structure
- [x] Handle invalid JSON responses
- [x] Add provider tests

### 1.3 Business Search

- [x] Implement BusinessSearchService
- [x] Validate maximum result input
- [x] Support configurable result limits
- [x] Implement pagination
- [x] Resolve supported Google redirect URLs
- [x] Integrate business mapping
- [x] Integrate deduplication
- [x] Support dependency injection
- [x] Support context manager lifecycle
- [x] Add search service tests

### 1.4 Business Models and Mapping

- [x] Create Business model
- [x] Implement Serper result mapping
- [x] Handle missing business information
- [x] Implement fallback business names
- [x] Normalize website URLs
- [x] Normalize phone numbers
- [x] Implement processing result models
- [x] Isolate individual mapping failures
- [x] Correct mapping failure indexes
- [x] Add model and mapper tests

### 1.5 Website Scraping

- [x] Implement HTTP-based website retrieval
- [x] Implement HTML processing
- [x] Implement response-size controls
- [x] Implement URL validation utilities
- [x] Implement initial SSRF protection
- [x] Handle individual website failures
- [x] Add website scraper tests

### 1.6 Contact Extraction

- [x] Implement email extraction
- [x] Implement phone extraction
- [x] Implement phone normalization
- [x] Implement contact deduplication
- [x] Discover contact pages
- [x] Discover relevant about pages
- [x] Implement ContactDiscoveryService
- [x] Add contact extraction tests
- [x] Add contact discovery tests

### 1.7 Business Deduplication

- [x] Implement BusinessDeduplicationService
- [x] Implement website-based matching
- [x] Implement phone-based matching
- [x] Implement name and address matching
- [x] Merge compatible contact information
- [x] Add deduplication tests

### 1.8 Lead Scoring

- [x] Implement rule-based lead scoring
- [x] Implement lead quality classification
- [x] Add scoring tests

### 1.9 Export

- [x] Implement Excel export
- [x] Implement CSV export
- [x] Support multiple email addresses
- [x] Support multiple phone numbers
- [x] Support international character encoding
- [x] Implement spreadsheet formula injection protection
- [x] Add exporter tests

### 1.10 CLI Integration

- [x] Integrate business discovery pipeline
- [x] Integrate contact discovery
- [x] Integrate export functionality
- [x] Execute initial live search tests
- [x] Verify baseline automated tests
- [x] Verify baseline Ruff checks
- [x] Verify baseline GitHub Actions CI

Status:
Functional backend prototype implemented.
Production readiness has not yet been established.

---

## Phase 2 — Backend Audit and Stabilization

### 2.1 Baseline Verification

- [x] Run complete pytest suite
- [x] Record exact test count
- [x] Run Ruff linting
- [x] Run Ruff formatting checks
- [x] Review test warnings
- [x] Verify dependency declarations
- [x] Review GitHub Actions configuration
- [ ] Establish updated backend checkpoint

### 2.2 Architecture Audit

- [x] Review package structure
- [x] Review component responsibilities
- [x] Review dependency direction
- [x] Identify unnecessary dependencies
- [x] Identify duplicated business logic
- [x] Review exception handling consistency
- [x] Review resource lifecycle management
- [x] Identify excessive coupling
- [x] Record architectural findings

### 2.3 Business Model Audit

- [x] Compare Business model against FR-05
- [x] Review field types and validation
- [x] Review missing-value representation
- [x] Review mutable collection handling
- [x] Add missing geographic fields
- [x] Add source information
- [x] Add contact page information
- [x] Add extraction status
- [x] Review lead score and quality representation
- [x] Update affected services and exporters
- [x] Add regression tests

Persistent identifiers and database timestamps may be
introduced during the persistence phase.

### 2.4 Search Provider Audit

- [x] Review request payload construction
- [x] Review API response validation
- [x] Review retryable failure classification
- [x] Review rate limiting
- [x] Review Retry-After behavior
- [x] Review timeout configuration
- [x] Review pagination termination
- [x] Review duplicate result handling
- [x] Review redirect resolution
- [x] Review provider resource cleanup
- [x] Review API credit consumption
- [x] Fix confirmed defects
- [x] Add regression tests

### 2.5 Contact Discovery Audit

- [x] Review website fetch behavior
- [x] Review contact page discovery
- [x] Review internal and external link handling
- [x] Review duplicate page detection
- [x] Review email extraction accuracy
- [x] Review phone extraction accuracy
- [x] Review false-positive handling
- [x] Review source tracking
- [x] Review partial extraction failures
- [x] Review preservation of provider contact data
- [x] Review extraction limits
- [x] Add regression tests

### 2.6 Security Audit

- [x] Review URL parsing and validation
- [x] Review private IP address blocking
- [x] Review loopback address blocking
- [x] Review link-local address blocking
- [x] Review IPv4 and IPv6 handling
- [x] Review DNS resolution
- [x] Review DNS rebinding protection
- [x] Review redirect safety
- [x] Review unsafe URL schemes
- [x] Review URL credential handling
- [x] Review response-size limits
- [x] Review request timeout limits
- [x] Review spreadsheet formula injection protection
- [x] Review secret management
- [x] Review and reduce sensitive information in local logs; production structured logging pending
- [x] Fix confirmed security defects
- [x] Add security regression tests

### 2.7 Deduplication Audit

- [x] Review domain normalization
- [x] Review shared website domains
- [x] Review shared phone numbers
- [x] Review business name normalization
- [x] Review address matching
- [x] Review multiple business branches
- [x] Review merge conflict handling
- [x] Review incorrect merge risks
- [x] Review duplicate detection across search pages
- [x] Add regression tests

### 2.8 Lead Scoring Audit

- [x] Verify scoring against documented requirements
- [x] Verify maximum score
- [x] Verify classification boundaries
- [x] Review incomplete contact information
- [x] Review score recalculation after merging
- [x] Ensure score represents information completeness
- [x] Add missing boundary tests

### 2.9 Export Audit

- [x] Compare Excel and CSV field definitions
- [x] Review missing-value handling
- [x] Review international character encoding
- [x] Review spreadsheet formula injection safeguards
- [x] Review output path safety
- [x] Review large export behavior
- [x] Review empty exports
- [x] Add regression tests

### 2.10 Backend Stabilization Gate

- [x] Record all identified audit findings
- [x] Classify findings by severity
- [x] Address identified local critical security issues; production review pending
- [x] Address identified local blocking reliability issues
- [x] Address identified local data corruption risks; persistent data review pending
- [x] Document deferred technical debt
- [x] Run complete test suite
- [x] Pass Ruff checks
- [x] Perform controlled live integration tests
- [ ] Pass GitHub Actions CI
- [ ] Update project status

Exit criteria:
The existing backend is sufficiently secure, reliable,
testable and reusable to support the next phase.

---

## Phase 3 — International Discovery Improvements

### 3.1 Search Input

- [x] Establish structured search input model
- [x] Validate country codes
- [x] Validate city input
- [x] Validate search query
- [x] Validate maximum results
- [x] Implement consistent query construction
- [x] Remove inappropriate hardcoded Nepal assumptions

### 3.2 Geographic Compatibility

- [x] Propagate country context through the pipeline
- [x] Implement region-aware phone normalization
- [x] Preserve internationally formatted phone numbers
- [x] Distinguish requested and discovered locations
- [x] Support missing geographic information
- [x] Review address parsing strategy
- [x] Test international business records

### 3.3 Discovery Quality

- [x] Review official website identification
- [x] Identify unrelated directory and article results
- [x] Preserve businesses without websites
- [x] Track website validation outcomes
- [x] Improve extraction source tracking
- [x] Establish extraction status definitions
- [ ] Improve contact relevance where practical

- [x] Implement optional organic website acquisition and aggregate diagnostics (AUD-033)
- [ ] Demonstrate live fallback recovery effectiveness (deferred)

### 3.4 Pipeline Orchestration

- [x] Review main.py responsibilities
- [x] Extract reusable pipeline orchestration
- [x] Introduce structured pipeline input
- [x] Introduce structured pipeline output
- [x] Introduce processing reports
- [x] Support progress reporting callbacks
- [x] Support individual business failure isolation
- [x] Decouple pipeline from CLI input and output
- [x] Decouple pipeline from file export
- [x] Add pipeline integration tests

### 3.5 Verification

- [x] Test Nepal-based searches
- [x] Test international searches
- [x] Test searches with no results
- [x] Test partial extraction failures
- [x] Verify requested maximum result handling
- [x] Inspect international Excel exports and verify automated CSV/Excel parity
- [ ] Independently inspect live CSV parity
- [x] Pass automated verification
- [ ] Update project status

Exit criteria:
The discovery pipeline operates independently of
the CLI and supports international business searches.

---

## Phase 4 — Database and Persistence

### 4.1 Database Architecture

- [ ] Evaluate relational database options
- [ ] Select database engine
- [ ] Select ORM or database access strategy
- [ ] Select migration tooling
- [ ] Document architectural decisions
- [ ] Configure development database
- [ ] Establish test database strategy

### 4.2 Database Schema

- [ ] Design users table
- [ ] Design businesses table
- [ ] Design business contacts table
- [ ] Design business sources table
- [ ] Design geographic representation
- [ ] Design search queries table
- [ ] Design search jobs table
- [ ] Design search result relationships
- [ ] Design processing failure records
- [ ] Define primary and foreign keys
- [ ] Define uniqueness constraints
- [ ] Define database indexes
- [ ] Review branch identity strategy
- [ ] Create initial migrations

### 4.3 Persistence Layer

- [ ] Implement database connection management
- [ ] Implement repository or data access layer
- [ ] Implement business insertion
- [ ] Implement business retrieval
- [ ] Implement business updates
- [ ] Implement contact merging
- [ ] Preserve historical website/contact observations, verification and freshness
- [ ] Implement persistent website cache and geographic enrichment cache
- [ ] Separate search geography from actual business geography
- [ ] Implement source persistence
- [ ] Implement transaction management
- [ ] Handle database failures
- [ ] Add database integration tests

### 4.4 Duplicate Search Detection

- [ ] Define normalized query identity
- [ ] Persist country, city and query
- [ ] Track requested maximum result count
- [ ] Detect existing search results
- [ ] Support reuse of previous results
- [ ] Support explicit re-fetch
- [ ] Prevent unintended duplicate jobs
- [ ] Preserve results from different searches
- [ ] Add duplicate search tests

### 4.5 Database-backed Export

- [ ] Retrieve available countries
- [ ] Retrieve available cities
- [ ] Retrieve businesses by geographic filters
- [ ] Export stored businesses to Excel
- [ ] Export stored businesses to CSV
- [ ] Verify consistent export fields
- [ ] Add persistence and export integration tests

Exit criteria:
Businesses, contacts, search history and results
are stored persistently without unnecessary duplication.

---

## Phase 5 — FastAPI Backend

### 5.1 API Foundation

- [ ] Introduce FastAPI
- [ ] Establish application structure
- [ ] Configure application settings
- [ ] Configure dependency injection
- [ ] Establish request and response schemas
- [ ] Establish consistent API error responses
- [ ] Configure structured logging
- [ ] Implement health endpoint
- [ ] Configure API documentation

### 5.2 Planned API Operations

- [ ] Submit discovery job
- [ ] Check duplicate query
- [ ] Retrieve job status
- [ ] Retrieve job progress
- [ ] Retrieve search history
- [ ] Retrieve available countries
- [ ] Retrieve available cities
- [ ] Download Excel export
- [ ] Download CSV export

Endpoint paths will be finalized during API design.

### 5.3 API Verification

- [ ] Test request validation
- [ ] Test response serialization
- [ ] Test invalid requests
- [ ] Test database failures
- [ ] Test API error responses
- [ ] Test export responses
- [ ] Review OpenAPI documentation

Exit criteria:
The frontend can interact with the backend through
documented and tested API operations.

---

## Phase 6 — Background Job Processing

- [ ] Evaluate background job technologies
- [ ] Select appropriately sized infrastructure
- [ ] Define job lifecycle
- [ ] Define job state transitions
- [ ] Implement job submission
- [ ] Implement worker execution
- [ ] Integrate reusable discovery pipeline
- [ ] Persist job progress
- [ ] Persist partial results
- [ ] Persist failure information
- [ ] Implement bounded job retries
- [ ] Implement job timeout handling
- [ ] Handle interrupted jobs
- [ ] Review cancellation behavior
- [ ] Prevent unintended duplicate execution
- [ ] Enforce shared Serper rate limits
- [ ] Enforce shared API usage limits
- [ ] Enforce bounded worker resources
- [ ] Test simultaneous job submissions
- [ ] Test worker failure and recovery
- [ ] Test partial job completion

Exit criteria:
Search jobs can execute independently of browser
requests with reliable progress and failure reporting.

---

## Phase 7 — React Frontend

### 7.1 Frontend Foundation

- [ ] Initialize React application
- [ ] Configure frontend project structure
- [ ] Establish reusable UI components
- [ ] Configure routing
- [ ] Configure API client
- [ ] Configure environment settings
- [ ] Establish loading and error states

### 7.2 Login Page

- [ ] Create login form
- [ ] Validate login input
- [ ] Display authentication errors
- [ ] Integrate authentication API
- [ ] Implement logout
- [ ] Protect application routes

### 7.3 Extraction Page

- [ ] Create country selector
- [ ] Create city input
- [ ] Create business query input
- [ ] Create maximum results input
- [ ] Implement form validation
- [ ] Implement duplicate query notification
- [ ] Implement reuse or re-fetch decision
- [ ] Implement job submission
- [ ] Display job status
- [ ] Display processing progress
- [ ] Display partial failure information

### 7.4 Export Page

- [ ] Retrieve available countries
- [ ] Implement country filter
- [ ] Retrieve available cities
- [ ] Implement city filter
- [ ] Implement Excel download
- [ ] Implement CSV download
- [ ] Handle empty export results
- [ ] Handle download failures

### 7.5 Frontend Verification

- [ ] Test forms
- [ ] Test API integration
- [ ] Test loading states
- [ ] Test error states
- [ ] Test protected routes
- [ ] Review responsive layout
- [ ] Review usability with company employees

Exit criteria:
Employees can submit discovery jobs and download
stored leads through the web interface.

---

## Phase 8 — Authentication and Authorization

Security design must begin before exposing protected
API operations or connecting the frontend to real data.

- [ ] Select authentication mechanism
- [ ] Define user access requirements
- [ ] Establish secure password handling if applicable
- [ ] Implement login backend
- [ ] Implement logout behavior
- [ ] Implement session or token validation
- [ ] Implement session expiration
- [ ] Protect discovery endpoints
- [ ] Protect job status endpoints
- [ ] Protect export endpoints
- [ ] Protect business data
- [ ] Implement account provisioning
- [ ] Implement account disabling
- [ ] Review brute-force protection
- [ ] Review CSRF requirements
- [ ] Review CORS configuration
- [ ] Test unauthorized access
- [ ] Test expired credentials
- [ ] Test access restrictions

Exit criteria:
Only authorized employees can access application
operations and stored business information.

---

## Phase 9 — Performance and Extraction Improvements

Begin after the backend stabilization gate.
Implement improvements based on measured need.

### 9.1 Performance Measurement

- [ ] Measure search duration
- [ ] Measure website extraction duration
- [ ] Measure total job duration
- [ ] Measure memory consumption
- [ ] Measure API consumption
- [ ] Identify major bottlenecks
- [ ] Establish realistic performance targets

### 9.2 Controlled Concurrency

- [ ] Evaluate threading versus asynchronous I/O
- [ ] Select concurrency approach
- [ ] Implement bounded concurrent extraction
- [ ] Enforce per-host request limits
- [ ] Preserve provider-wide rate limits
- [ ] Review thread or task safety
- [ ] Review cancellation and cleanup
- [ ] Test concurrent failures
- [ ] Benchmark against sequential processing

### 9.3 Browser Automation — Optional

- [ ] Measure JavaScript-dependent extraction failures
- [ ] Determine whether browser automation is justified
- [ ] Evaluate Playwright
- [ ] Define fallback eligibility
- [ ] Define browser resource limits
- [ ] Review browser network security
- [ ] Prevent unnecessary browser launches
- [ ] Test browser lifecycle management
- [ ] Benchmark extraction improvements

Do not implement Playwright unless the benefit
justifies the additional complexity and resource cost.

---

## Phase 10 — Production Security and Quality Assurance

### 10.1 Security

- [ ] Complete backend security review
- [ ] Complete API security review
- [ ] Complete authentication security review
- [ ] Review production secrets
- [ ] Review external request restrictions
- [ ] Review database access permissions
- [ ] Review dependency vulnerabilities
- [ ] Review export access controls
- [ ] Review rate and resource limits
- [ ] Review sensitive data exposure
- [ ] Establish security update procedures

### 10.2 Data Privacy

- [ ] Review permitted data collection
- [ ] Review website access restrictions
- [ ] Define data retention policy
- [ ] Define record deletion procedures
- [ ] Review business contact data handling
- [ ] Review employee access permissions

### 10.3 Testing

- [ ] Complete unit tests
- [ ] Complete integration tests
- [ ] Complete API tests
- [ ] Complete database tests
- [ ] Complete security tests
- [ ] Complete end-to-end tests
- [ ] Test multiple users
- [ ] Test duplicate searches
- [ ] Test provider failures
- [ ] Test worker failures
- [ ] Test database failures
- [ ] Test international discovery
- [ ] Validate Excel and CSV exports
- [ ] Conduct user acceptance testing

Exit criteria:
No unresolved release-blocking defects.

---

## Phase 11 — Production Deployment

### 11.1 Infrastructure Planning

- [ ] Evaluate hosting options
- [ ] Estimate operating costs
- [ ] Select hosting infrastructure
- [ ] Establish development environment
- [ ] Establish staging environment
- [ ] Establish production environment
- [ ] Document infrastructure decisions

### 11.2 Deployment Preparation

- [ ] Containerize API where appropriate
- [ ] Containerize workers where appropriate
- [ ] Configure frontend production build
- [ ] Configure production database
- [ ] Configure job infrastructure
- [ ] Configure environment secrets
- [ ] Configure database migrations
- [ ] Configure persistent storage
- [ ] Configure HTTPS
- [ ] Configure domain or subdomain
- [ ] Configure production access restrictions
- [ ] Configure repeatable deployment workflow

### 11.3 Deployment Verification

- [ ] Deploy to staging
- [ ] Run staging smoke tests
- [ ] Test complete discovery workflow
- [ ] Test authentication
- [ ] Test background processing
- [ ] Test database persistence
- [ ] Test Excel and CSV downloads
- [ ] Test backup and restoration
- [ ] Establish rollback procedure
- [ ] Obtain stakeholder approval
- [ ] Deploy to production
- [ ] Run production smoke tests
- [ ] Provision employee accounts
- [ ] Prepare user instructions

Exit criteria:
Authorized employees can securely use the hosted
application for real business discovery operations.

---

## Phase 12 — Monitoring and Maintenance

### 12.1 Operational Monitoring

- [ ] Configure application logs
- [ ] Configure error reporting
- [ ] Monitor application availability
- [ ] Monitor worker health
- [ ] Monitor failed jobs
- [ ] Monitor database health
- [ ] Monitor processing durations
- [ ] Monitor resource consumption

### 12.2 Cost Control

- [ ] Track Serper API consumption
- [ ] Establish API usage budgets
- [ ] Configure consumption thresholds
- [ ] Monitor duplicate query frequency
- [ ] Monitor retry-related consumption
- [ ] Monitor hosting expenses
- [ ] Document API credit management

### 12.3 Recovery and Maintenance

- [ ] Schedule database backups
- [ ] Verify backup integrity
- [ ] Test periodic restoration
- [ ] Establish dependency update procedures
- [ ] Establish security patch procedures
- [ ] Establish incident response procedures
- [ ] Maintain operational documentation
- [ ] Collect employee feedback
- [ ] Prioritize confirmed defects
- [ ] Maintain future enhancement backlog

---

## Future Enhancements — Not Required for Initial Release

- [ ] Advanced lead filtering
- [ ] Business management dashboard
- [ ] Configurable scoring rules
- [ ] Scheduled discovery jobs
- [ ] Additional search providers
- [ ] Advanced address normalization
- [ ] Search result analytics
- [ ] CRM integration
- [ ] Machine learning-based qualification

Future enhancements require explicit approval and
must not delay the initial production release.

---

## Roadmap Maintenance Rules

- Follow AGENTS.md.
- Complete one implementation task at a time.
- Verify existing code before modifying it.
- Do not mark unverified implementation as complete.
- Record significant architectural decisions.
- Record audit findings and technical debt.
- Update the roadmap after verified changes.
- Prioritize blocking security and reliability issues.
- Avoid premature optimization.
- Maintain the project status document.
- Reconcile documentation with repository evidence.

## Current Development Position

Date: 26 November 2026

Phase 2 local stabilization and Phase 3 international CLI core verified. Final checkpoint documentation, commit and exact-commit CI remain pending. Next: Phase 4 PostgreSQL design after closure. Deferred extraction and geography items do not imply production readiness.

Local verification on 26 November 2026 (Python 3.13.17, Windows):

- 1,173 tests passed in 19.79 seconds; 96% statement coverage (2,012 statements, 80 missed). Coverage excludes main.py and is not branch coverage.
- pip check and Ruff lint passed; 86 Python files formatted; staged and unstaged diff checks clean.
- Both declared-dependency and installed-environment pip-audit scans reported no known vulnerabilities earlier in the session; no dependencies changed in the final acquisition batch.
- Gitleaks: 38 commits / approximately 706,801 bytes of history and 14,197 bytes of staged changes scanned; no leaks, both exit codes 0. .env ignored, untracked and absent from available history.
- Latest acquisition changes: 11 staged files, 337 insertions, 2 deletions, based on 7bc9e25. Final commit and remote CI not yet verified.

See BACKEND_AUDIT.md for residual risks and PROJECT_STATUS.md for live evidence.
