import csv
from unittest.mock import Mock, patch

from openpyxl import load_workbook

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.search.serper_provider import SerperSearchProvider
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.services.lead_scoring import LeadScoringService

CONTACT_MODULE = "src.lead_intelligence.services.contact_discovery"


def read_csv(path):
    with open(
        path,
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def read_excel(path):
    workbook = load_workbook(path)

    try:
        rows = list(workbook.active.iter_rows(values_only=True))

        headers = rows[0]

        return [dict(zip(headers, row, strict=True)) for row in rows[1:]]

    finally:
        workbook.close()


def test_complete_business_pipeline(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    raw_results = {
        "places": [
            {
                "title": "Nepal Adventure",
                "website": "https://example.com",
                "phoneNumber": "9846041887",
                "address": "Thamel, Kathmandu",
                "category": "Travel agency",
            }
        ]
    }

    mock_post = Mock(
        side_effect=[
            raw_results,
            {"places": []},
        ]
    )

    monkeypatch.setattr(
        provider,
        "_post",
        mock_post,
    )

    # Stage 1: Search and mapping.
    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Trekking companies in Kathmandu",
            country="np",
        )

    assert result.total_discovered == 1
    assert result.total_mapped == 1
    assert result.total_failed == 0
    assert result.total_returned == 1

    business = result.businesses[0]

    assert business.name == "Nepal Adventure"
    assert business.phone_numbers == ["+9779846041887"]
    assert business.extraction_status == ExtractionStatus.PENDING
    assert business.lead_score is None

    # Stage 2: Contact discovery.
    homepage_html = """
        <html>
            <body>
                <p>info@example.com</p>
                <a href="/contact">Contact us</a>
            </body>
        </html>
    """

    with (
        patch(
            f"{CONTACT_MODULE}.fetch_website_html",
            return_value=homepage_html,
        ) as mock_homepage,
        patch(
            f"{CONTACT_MODULE}.fetch_website",
            return_value=("sales@example.com +97714989212"),
        ) as mock_contact_page,
    ):
        ContactDiscoveryService().discover(
            business,
            region="NP",
        )

    mock_homepage.assert_called_once_with("https://example.com")

    mock_contact_page.assert_called_once_with("https://example.com/contact")

    assert business.emails == [
        "info@example.com",
        "sales@example.com",
    ]

    assert business.phone_numbers == [
        "+9779846041887",
        "+97714989212",
    ]

    assert business.source_urls == [
        "https://example.com",
        "https://example.com/contact",
    ]

    assert business.contact_page_urls == [
        "https://example.com/contact",
    ]

    assert business.extraction_status == ExtractionStatus.SUCCESS

    # Search location must not become assumed business geography.
    assert business.country_code is None

    # Stage 3: Lead evaluation.
    scoring_service = LeadScoringService()

    scoring_service.evaluate_business(
        business,
        region="NP",
    )

    assert business.lead_score == 100
    assert business.lead_quality == "High"

    # Stage 4: Export.
    csv_path = tmp_path / "leads.csv"
    excel_path = tmp_path / "leads.xlsx"

    export_businesses_to_csv(
        result.businesses,
        str(csv_path),
        region="NP",
    )

    export_businesses_to_excel(
        result.businesses,
        str(excel_path),
        region="NP",
    )

    csv_rows = read_csv(csv_path)
    excel_rows = read_excel(excel_path)

    assert len(csv_rows) == 1
    assert len(excel_rows) == 1

    csv_row = csv_rows[0]
    excel_row = excel_rows[0]

    assert len(csv_row) == 16
    assert len(excel_row) == 16

    assert csv_row["Business Name"] == "Nepal Adventure"
    assert excel_row["Business Name"] == "Nepal Adventure"

    assert csv_row["Lead Score"] == "100"
    assert excel_row["Lead Score"] == 100

    assert csv_row["Lead Quality"] == "High"
    assert excel_row["Lead Quality"] == "High"

    assert csv_row["Extraction Status"] == "success"
    assert excel_row["Extraction Status"] == "success"

    assert csv_row["Country Code"] == ""
    assert excel_row["Country Code"] is None

    assert csv_row["Emails"] == ("info@example.com; sales@example.com")

    assert csv_row["Source URLs"] == (
        "https://example.com; https://example.com/contact"
    )

    assert mock_post.call_count == 2


def test_pipeline_handles_duplicates_and_mapping_failures(
    monkeypatch,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    raw_results = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://example.com",
            },
            {
                "title": "Example Business Pvt Ltd",
                "website": "https://www.example.com",
                "phoneNumber": "+9779846041887",
            },
            None,
            {
                "title": "Invalid Business",
                "address": 123,
            },
            {
                "title": "Business Without Website",
            },
        ]
    }

    monkeypatch.setattr(
        provider,
        "_post",
        Mock(
            side_effect=[
                raw_results,
                {"places": []},
            ]
        ),
    )

    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Travel agencies",
            country="np",
        )

    assert result.total_discovered == 5
    assert result.total_mapped == 3
    assert result.total_failed == 2
    assert result.duplicate_count == 1
    assert result.total_returned == 2

    assert [failure.item_index for failure in result.failures] == [2, 3]

    assert result.businesses[0].phone_numbers == ["+9779846041887"]

    contact_service = ContactDiscoveryService()

    with patch(
        f"{CONTACT_MODULE}.fetch_website_html",
        return_value="<p>info@example.com</p>",
    ) as mock_homepage:
        for business in result.businesses:
            contact_service.discover(
                business,
                region="NP",
            )

    mock_homepage.assert_called_once()

    assert result.businesses[0].extraction_status == (ExtractionStatus.SUCCESS)

    assert result.businesses[1].extraction_status == (ExtractionStatus.NO_WEBSITE)

    LeadScoringService().evaluate_businesses(
        result.businesses,
        region="NP",
    )

    assert result.businesses[0].lead_score == 80
    assert result.businesses[1].lead_score == 0


def test_pipeline_handles_partial_and_failed_extraction(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    raw_results = {
        "places": [
            {
                "title": "Partial Business",
                "website": "https://partial.example.com",
            },
            {
                "title": "Failed Business",
                "website": "https://failed.example.com",
                "phoneNumber": "+9779846041887",
            },
        ]
    }

    monkeypatch.setattr(
        provider,
        "_post",
        Mock(return_value=raw_results),
    )

    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Travel agencies",
            country="np",
        )

    homepage_html = """
        <html>
            <body>
                info@example.com
                <a href="/contact">Contact us</a>
            </body>
        </html>
    """

    contact_service = ContactDiscoveryService()

    with (
        patch(
            f"{CONTACT_MODULE}.fetch_website_html",
            side_effect=[homepage_html, None],
        ),
        patch(
            f"{CONTACT_MODULE}.fetch_website",
            return_value=None,
        ),
    ):
        for business in result.businesses:
            contact_service.discover(
                business,
                region="NP",
            )

    partial_business = result.businesses[0]
    failed_business = result.businesses[1]

    assert partial_business.extraction_status == (ExtractionStatus.PARTIAL)

    assert partial_business.emails == ["info@example.com"]

    assert partial_business.source_urls == ["https://partial.example.com"]

    assert failed_business.extraction_status == (ExtractionStatus.FAILED)

    assert failed_business.phone_numbers == ["+9779846041887"]

    LeadScoringService().evaluate_businesses(
        result.businesses,
        region="NP",
    )

    assert partial_business.lead_score == 60
    assert failed_business.lead_score == 50

    output_path = tmp_path / "partial_leads.csv"

    export_businesses_to_csv(
        result.businesses,
        str(output_path),
    )

    rows = read_csv(output_path)

    assert len(rows) == 2

    assert rows[0]["Extraction Status"] == "partial"
    assert rows[1]["Extraction Status"] == "failed"

    assert rows[0]["Lead Score"] == "60"
    assert rows[1]["Lead Score"] == "50"


def test_pipeline_resolves_google_redirects(
    monkeypatch,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    raw_results = {
        "places": [
            {
                "title": "Example Business",
                "website": ("https://google.com/goto?url=example"),
            }
        ]
    }

    resolved_results = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://example.com",
            }
        ]
    }

    mock_post = Mock(
        side_effect=[
            raw_results,
            resolved_results,
            {"places": []},
        ]
    )

    monkeypatch.setattr(
        provider,
        "_post",
        mock_post,
    )

    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Travel agencies",
            country="np",
        )

    assert mock_post.call_count == 3
    assert mock_post.call_args_list[0].args[0] == "places"
    assert mock_post.call_args_list[1].args[0] == "resolve"

    business = result.businesses[0]

    assert business.website == "https://example.com"

    with patch(
        f"{CONTACT_MODULE}.fetch_website_html",
        return_value="<p>info@example.com</p>",
    ) as mock_homepage:
        ContactDiscoveryService().discover(
            business,
        )

    mock_homepage.assert_called_once_with("https://example.com")

    assert business.extraction_status == (ExtractionStatus.SUCCESS)

    assert business.source_urls == ["https://example.com"]

    LeadScoringService().evaluate_business(business)

    assert business.lead_score == 60


def test_empty_pipeline_exports_valid_files(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    monkeypatch.setattr(
        provider,
        "_post",
        Mock(return_value={"places": []}),
    )

    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Travel agencies",
        )

    assert result.total_discovered == 0
    assert result.total_returned == 0
    assert result.total_failed == 0

    LeadScoringService().evaluate_businesses(result.businesses)

    csv_path = tmp_path / "empty.csv"
    excel_path = tmp_path / "empty.xlsx"

    export_businesses_to_csv(
        result.businesses,
        str(csv_path),
    )

    export_businesses_to_excel(
        result.businesses,
        str(excel_path),
    )

    assert csv_path.exists()
    assert excel_path.exists()

    assert read_csv(csv_path) == []
    assert read_excel(excel_path) == []

    with open(
        csv_path,
        encoding="utf-8-sig",
        newline="",
    ) as file:
        assert len(next(csv.reader(file))) == 16

    workbook = load_workbook(excel_path)

    try:
        assert workbook.active.max_row == 1
        assert workbook.active.max_column == 16

    finally:
        workbook.close()


def test_pipeline_supports_international_search_regions(
    monkeypatch,
):
    monkeypatch.setenv(
        "SERPER_API_KEY",
        "test-api-key",
    )

    provider = SerperSearchProvider()

    mock_post = Mock(
        return_value={
            "places": [
                {
                    "title": "American Travel Agency",
                    "website": "https://example.com",
                    "phoneNumber": "2025550123",
                    "address": "Washington, DC",
                    "category": "Travel agency",
                }
            ]
        }
    )

    monkeypatch.setattr(
        provider,
        "_post",
        mock_post,
    )

    with BusinessSearchService(provider=provider) as search_service:
        result = search_service.search_with_report(
            query="Travel agencies in Washington",
            country=" US ",
        )

    assert mock_post.call_args.args[1]["gl"] == "us"

    business = result.businesses[0]

    assert business.phone_numbers == ["+12025550123"]

    with patch(
        f"{CONTACT_MODULE}.fetch_website_html",
        return_value="<p>sales@example.com</p>",
    ):
        ContactDiscoveryService().discover(
            business,
            region="US",
        )

    LeadScoringService().evaluate_business(
        business,
        region="US",
    )

    assert business.emails == ["sales@example.com"]
    assert business.country_code is None
    assert business.lead_score == 100
    assert business.lead_quality == "High"
