# Business Lead Intelligence Platform

A Python-based business lead intelligence platform designed to discover businesses, collect their contact information, validate and normalize business data, identify duplicate records, calculate lead quality scores, and export qualified leads to Excel and CSV.

## Project Goals

- Discover businesses using Serper Places Search.
- Collect structured business information.
- Visit official business websites.
- Extract email addresses and phone numbers.
- Discover contact, about, and related business pages.
- Validate and normalize extracted information.
- Identify duplicate business records.
- Calculate lead quality scores.
- Export business leads to Excel and CSV.

## Current Features

- Serper Places and Resolve integration, bounded pagination and credit reporting.
- Optional budget-controlled organic website discovery with conservative name/phone verification and outcome counters.
- Reusable pipeline, international request validation, CID-aware deduplication and offline geographic enrichment.
- Contact source provenance, extraction status and atomic per-file exports.
- Business search with configurable result limits.
- HTTP request retry and rate limiting.
- Website scraping with redirect and response-size controls.
- Contact page discovery.
- Email extraction and validation.
- Phone number extraction and regional normalization.
- Business deduplication.
- Lead scoring and quality classification.
- Excel export using OpenPyXL.
- CSV export using Python's built-in CSV module.
- Automated tests using pytest.
- Code quality checks using Ruff.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application |
| Serper API | Business discovery |
| Requests | HTTP requests |
| HTTPX | Website scraping |
| BeautifulSoup | HTML parsing |
| Phonenumbers | Phone validation and normalization |
| OpenPyXL | Excel export |
| FastAPI | Planned API backend |
| PostgreSQL | Planned database |
| React + TypeScript | Planned frontend |
| Pytest | Automated testing |
| Ruff | Linting and formatting |

## Prerequisites

- Python 3.13 (verified locally on 3.13.17).
- Git.
- A Serper API key.

## Installation

Clone the repository:

```bash
git clone https://github.com/aspirationasiatrekking/business-lead-intelligence.git
cd business-lead-intelligence
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

### Dependency Management

- `requirements.txt`: Runtime dependencies.
- `requirements-dev.txt`: Runtime and development dependencies.

For development:

    python -m pip install -r requirements-dev.txt

For runtime-only installation:

    python -m pip install -r requirements.txt

## Environment Configuration

Copy `.env.example` to `.env` in the project root (do not overwrite an existing configuration).

Add your Serper API key:

```env
SERPER_API_KEY=your_serper_api_key
```

Never commit your `.env` file or expose API keys publicly. See `.env.example` for optional bounds; `MAX_WEBSITE_SEARCHES=0` disables paid organic fallback. Environment variables override the file.

## Running the Application

Run the current application:

```bash
python main.py
```

## Running Tests

The CLI prompts for ISO country code, city, query and 1–100 results. Outputs are written to a unique run directory under `output/` by default.

Run the complete test suite:

```bash
python -m pytest --cov=src/lead_intelligence --cov-report=term-missing
```

Run Ruff lint checks:

```bash
python -m ruff check .
```

Check code formatting:

```bash
python -m ruff format --check .
```

## Project Status

The current implementation is a locally verified, reusable Python discovery core. Final checkpoint CI is pending; it is not a production application.

Local verification on 26 November 2026 (Python 3.13.17, Windows):

- 1,173 tests passed in 19.79 seconds; 96% statement coverage (2,012 statements, 80 missed). Coverage excludes main.py and is not branch coverage.
- pip check and Ruff lint passed; 86 Python files formatted; staged and unstaged diff checks clean.
- Both declared-dependency and installed-environment pip-audit scans reported no known vulnerabilities earlier in the session; no dependencies changed in the final acquisition batch.
- Gitleaks: 38 commits / approximately 706,801 bytes of history and 14,197 bytes of staged changes scanned; no leaks, both exit codes 0. .env ignored, untracked and absent from available history.
- Latest acquisition changes: 11 staged files, 337 insertions, 2 deletions, based on 7bc9e25. Final commit and remote CI not yet verified.

Known limitations and next steps: see [Project Status](docs/PROJECT_STATUS.md) and [Backend Audit](docs/BACKEND_AUDIT.md).

The following capabilities are planned:

- Database persistence using PostgreSQL.
- Country and city-based business organization.
- Search history and search result reuse.
- FastAPI backend.
- User authentication and role management.
- Background search processing.
- React frontend.
- Multi-user company access.
- Production deployment and security hardening.

## Security

- API credentials are stored in environment variables.
- `.env` must remain excluded from version control.
- Website requests include URL safety checks and response-size limits.
- Connection-time public IP validation, DNS rebinding mitigation, redirect restrictions and bounded response handling are implemented and locally tested. Production network isolation and application security remain pending.

## License

Internal company project. No public license has been assigned.


## Project Documentation

| Document | Description |
|---|---|
| [Engineering Instructions](AGENTS.md) | Development rules and engineering standards |
| [Project Context](docs/PROJECT_CONTEXT.md) | Business objectives and project scope |
| [Requirements](docs/REQUIREMENTS.md) | Functional and non-functional requirements |
| [Architecture](docs/ARCHITECTURE.md) | Current and planned system architecture |
| [Master Roadmap](docs/ROADMAP.md) | Development checklist through production |
| [Project Status](docs/PROJECT_STATUS.md) | Latest development checkpoint |
| [Architectural Decisions](docs/DECISIONS.md) | Technical decisions and rationale |
| [Backend Audit](docs/BACKEND_AUDIT.md) | Audit findings and technical debt |
| [Development Log](docs/DEVELOPMENT_LOG.md) | Development history and verification |

### Continuing Development

Before starting a new development session:

1. Read AGENTS.md.
2. Read docs/PROJECT_STATUS.md.
3. Read docs/ROADMAP.md.
4. Review recent development log entries.
5. Inspect the current repository state.
6. Continue with the next unfinished task.