
# Business Lead Intelligence — System Architecture

## 1. Architecture Overview

The platform follows a modular, layered architecture.

Business discovery, contact extraction, normalization,
deduplication, scoring, and export are implemented
independently of the future web interface.

Development follows a backend-first approach.

## 2. Current Architecture

The current application is a Python CLI-based backend.

Conceptual processing pipeline:

    CLI
     |
     v
    Business Search Service
     |
     v
    Serper Places / Resolve API
     |
     v
    Business Mapping
     |
     v
    Contact Discovery
     |
     +-- Website Scraper
     +-- Contact Extractor
     |
     v
    Deduplication and Lead Scoring
     |
     v
    Excel / CSV Export

The precise execution order and component interactions
must be verified during the backend audit.

## 3. Current Repository Structure

    business-lead-intelligence/
    |
    |-- .github/workflows/
    |-- docs/
    |-- output/
    |-- src/lead_intelligence/
    |   |-- exporters/
    |   |-- extractors/
    |   |-- models/
    |   |-- scrapers/
    |   |-- search/
    |   |-- services/
    |   |-- utils/
    |-- tests/
    |-- .env.example
    |-- .gitignore
    |-- AGENTS.md
    |-- main.py
    |-- pyproject.toml
    |-- README.md
    |-- requirements.txt

## 4. Component Responsibilities

### CLI

Provides search input and coordinates the current
business discovery and export workflow.

### Search Provider

Responsible for:

- External search API communication
- Places search
- Redirect resolution
- Rate limiting
- Retry handling
- Response validation
- Network resource management

### Models and Mapping

Responsible for:

- Internal business representation
- External response mapping
- Data normalization
- Processing result representation
- Mapping failure isolation

### Website Scraper

Responsible for:

- Retrieving external website content
- HTTP request handling
- Response validation
- HTML processing
- Network safety controls

### Contact Extractor

Responsible for identifying and normalizing:

- Email addresses
- Phone numbers

### Contact Discovery Service

Coordinates website scraping and contact extraction.

Discovers relevant contact and about pages and
combines available contact information.

### Business Deduplication Service

Identifies duplicate business records and merges
compatible information according to defined rules.

### Lead Scoring Service

Calculates deterministic information completeness
scores and corresponding quality classifications.

### Exporters

Generate structured output in Excel and CSV formats.

Exporters must protect against formula injection
and support international characters.

### Utilities

Provide reusable URL normalization, validation,
and security functionality.

## 5. Target Production Architecture

    Company Employees
           |
           v
    React Frontend
           |
         HTTPS
           |
           v
       FastAPI
        /   \
       /     \
    Database  Job Queue
       ^         |
       |         v
       +---- Background Worker
                 |
                 v
           Discovery Pipeline
              /       \
             /         \
        Serper API   Business Websites

This is the intended logical architecture.

Physical deployment and infrastructure decisions
remain subject to architectural review.

## 6. Frontend Layer

Planned technology: React.

Responsibilities:

- Login
- Search input
- Duplicate query notification
- Job submission
- Job progress reporting
- Export filters
- Excel and CSV downloads

The frontend must not contain core scraping
or business discovery logic.

## 7. API Layer

Planned technology: FastAPI.

Responsibilities:

- Request validation
- Authentication and authorization
- Search job submission
- Duplicate query detection
- Job status retrieval
- Database-backed export operations
- User-facing error responses

API handlers must not directly execute long-running
website scraping operations.

## 8. Background Processing Layer

Background workers execute discovery jobs
independently of frontend requests.

Responsibilities:

- Business discovery
- Contact extraction
- Normalization
- Deduplication
- Lead scoring
- Result persistence
- Progress reporting
- Failure handling

The worker infrastructure must enforce shared
provider rate limits and bounded resource usage.

The queue technology has not been selected.

## 9. Persistence Layer

A relational database is planned.

The conceptual entities include:

- Users
- Businesses
- Business contacts
- Business sources
- Search queries
- Search jobs
- Search results
- Processing failures

A business may be discovered by multiple searches.

Search history and business records must not be
unnecessarily duplicated.

Country and city filters must be supported.

The final schema will be designed during the
database development phase.

## 10. Security Architecture

External websites and API responses are untrusted.

Security controls must include:

- Safe URL validation
- SSRF protection
- DNS rebinding mitigation
- Redirect validation
- Request timeouts
- Response-size limits
- Input validation
- Authentication
- Authorization
- Secure secret management
- Spreadsheet formula injection prevention

Existing security controls require further auditing.

Production traffic must use HTTPS.

## 11. Reliability Architecture

The platform must support:

- Bounded retries
- Provider rate limiting
- Individual business failure isolation
- Partial job completion
- Managed resource cleanup
- Transactional persistence
- Job recovery
- Structured logging
- Database backup and recovery

An individual website failure should not unnecessarily
terminate an entire discovery job.

## 12. Testing Architecture

Testing will be organized into:

- Unit tests
- Integration tests
- Security tests
- Regression tests
- API tests
- End-to-end tests

External APIs must be mocked during ordinary
automated testing.

Live provider tests must be controlled to avoid
unnecessary API credit consumption.

GitHub Actions provides automated verification.

## 13. Deployment Architecture

The target deployment should support:

- Hosted React frontend
- FastAPI application
- Background workers
- Relational database
- Secure environment configuration
- HTTPS
- Operational logs
- Health checks
- Database backups
- Repeatable deployment

Containerization is planned.

Specific hosting and infrastructure technologies
have not yet been selected.

## 14. Architectural Constraints

- Stabilize the backend before frontend implementation.
- Avoid premature concurrency.
- Keep the existing discovery pipeline reusable.
- Separate business logic from infrastructure.
- Do not introduce unnecessary dependencies.
- Maintain international compatibility.
- Prioritize security and data correctness.
- Preserve testability.

## 15. Pending Architectural Decisions

- Database engine
- ORM and migration tooling
- Background job queue
- Authentication mechanism
- Deployment infrastructure
- Concurrency model
- Browser automation fallback
- Logging and monitoring technologies
- Data retention and recovery policies

Record significant architectural decisions in
docs/DECISIONS.md.
