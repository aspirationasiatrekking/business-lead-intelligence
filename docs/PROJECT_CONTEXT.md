
# Business Lead Intelligence — Project Context

## 1. Project Information

- Project: Business Lead Intelligence
- Organization: Aspiration Asia Trekking
- Project type: Internal business intelligence platform
- Repository: https://github.com/aspirationasiatrekking/business-lead-intelligence
- Development approach: Backend-first
- Primary language: Python
- Intended users: Approximately 3–4 company employees initially

## 2. Problem Statement

Manually discovering businesses and collecting their contact
information is time-consuming, repetitive, difficult to scale,
and prone to human error.

Business information is distributed across search engines,
business listings, official websites, and contact pages.

The company requires a centralized platform that automates
business discovery, contact extraction, data normalization,
deduplication, storage, and export.

## 3. Project Objective

Build a reliable, secure, maintainable, and deployable
business lead intelligence platform that allows authorized
employees to discover and collect structured business leads
from different geographical regions.

## 4. Business Objectives

- Reduce manual business research.
- Reduce repetitive data entry.
- Improve contact information completeness.
- Reduce duplicate business records.
- Support international business discovery.
- Centralize collected business information.
- Allow employees to reuse previously collected results.
- Reduce unnecessary external API expenses.
- Export structured business leads for further business use.

## 5. Target Users

The initial users are company employees responsible for:

- Business development
- Market research
- Partnership discovery
- Lead generation
- Business outreach

The initial deployment should support approximately
3–4 authorized employees.

The architecture should allow future expansion without
requiring a complete system rewrite.

## 6. Initial Business Use Cases

The initial business focus includes discovering:

- Travel agencies
- Trekking companies
- Expedition operators
- Tour operators
- Adventure travel companies
- International travel partners

However, the platform must not be restricted to the travel
industry.

Business categories should be determined by user search
queries rather than hardcoded application logic.

## 7. Geographic Scope

The platform must support international business discovery.

Initial testing may include Nepalese locations such as:

- Kathmandu
- Bhaktapur
- Pokhara
- Chitwan
- Mustang

The application must also support other countries and cities.

Country-specific assumptions must not be embedded in
general-purpose business logic.

## 8. Intended User Workflow

1. Employee logs into the application.
2. Employee selects a country.
3. Employee enters a city or target location.
4. Employee enters a business search query.
5. Employee selects the maximum number of results.
6. Application checks for a previously executed query.
7. If a duplicate query exists, the employee is informed.
8. Employee may choose to reuse results or execute the query again.
9. Application creates a background discovery job.
10. Search provider discovers businesses.
11. Application maps external results into internal records.
12. Application discovers and validates business websites.
13. Contact extraction collects available contact information.
14. Application normalizes and deduplicates records.
15. Application calculates lead scores and quality labels.
16. Results are saved in persistent storage.
17. Employee receives job completion or failure information.
18. Employee accesses the export page.
19. Employee selects a country and city.
20. Employee downloads the available data as Excel or CSV.

## 9. Data Collection Scope

Collect relevant, publicly available business information,
including:

- Business name
- Business category
- Business address
- City
- District
- State or province
- Country
- Country code
- Official website
- Business email addresses
- Business phone numbers
- Source URLs
- Contact page URLs
- Extraction status
- Lead score
- Lead quality

Additional metadata may be introduced for auditing,
persistence, and operational requirements.

Do not fabricate missing information.

## 10. Project Boundaries

The platform is intended for legitimate business research.

The initial product does not include:

- Automated unsolicited email campaigns
- Automated social media messaging
- Personal profile scraping
- Collection of unnecessary sensitive personal information
- CAPTCHA bypass
- Authentication bypass
- Automatic purchasing of external API credits
- Machine learning-based lead qualification
- A complete customer relationship management system

Future features require explicit requirements and
architectural review.

## 11. Technology Direction

### Implemented or currently used

- Python
- Serper Places API
- Serper Resolve API
- Optional Serper organic Search API (disabled by default)
- Requests (provider)
- HTTPX/httpcore (secure website retrieval)
- BeautifulSoup
- Phonenumbers
- OpenPyXL
- Pytest
- Ruff
- Git
- GitHub Actions

### Planned

- FastAPI backend
- PostgreSQL (planned; schema and access strategy pending)
- Database migrations
- Background job processing
- React frontend
- Authentication and authorization
- Containerized deployment
- Production monitoring

Planned technologies are subject to architectural review
before implementation.

## 12. Development Strategy

The application will be developed incrementally.

The existing Python backend must be audited, stabilized,
and tested before introducing additional architectural layers.

Development priorities are:

1. Correctness
2. Security
3. Reliability
4. Maintainability
5. Testability
6. Performance
7. Usability

Refer to AGENTS.md for permanent engineering instructions.

## 13. Project Success Criteria

The project is successful when authorized employees can:

- Discover businesses internationally.
- Execute searches without developer assistance.
- Collect available business contact information.
- Track discovery job progress.
- Recover from individual website failures.
- Avoid unnecessary duplicate searches.
- Store and retrieve previously collected businesses.
- Download valid Excel and CSV files.
- Use the application securely through a hosted interface.

The system must also provide sufficient testing,
documentation, operational visibility, and recovery
mechanisms for ongoing company use.

## 14. Documentation Authority

The repository is the permanent source of truth.

Project requirements, architectural decisions, development
progress, and known issues must be maintained in
version-controlled documentation.

Conversation history must not be the only source of
important project information.
