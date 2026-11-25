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

- Serper Places API integration.
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
| XlsxWriter | Installed dependency; usage to be reviewed |
| FastAPI | Planned API backend |
| PostgreSQL | Planned database |
| React + TypeScript | Planned frontend |
| Pytest | Automated testing |
| Ruff | Linting and formatting |

## Prerequisites

- Python 3.13 or compatible version.
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

```bash
python -m pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root.

Add your Serper API key:

```env
SERPER_API_KEY=your_serper_api_key
```

Never commit your `.env` file or expose API keys publicly.

## Running the Application

Run the current application:

```bash
python main.py
```

## Running Tests

Run the complete test suite:

```bash
python -m pytest
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

The current implementation is a functional Python-based lead discovery and processing prototype.

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
- Production-grade SSRF protection and additional security hardening remain planned.

## License

Internal company project. No public license has been assigned.