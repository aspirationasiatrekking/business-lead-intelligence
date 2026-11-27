from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from src.lead_intelligence.database.exceptions import PersistenceValidationError
from src.lead_intelligence.database.services.location_export import (
    export_location,
    load_location_businesses,
    location_statement,
)

MODULE = "src.lead_intelligence.database.services.location_export"


def test_location_uses_search_history():
    compiled = location_statement("np", " Kathmandu ").compile(
        dialect=postgresql.dialect()
    )
    assert "search_results" in str(compiled)
    assert "search_queries.city_normalized" in str(compiled)
    assert "businesses.id IN" in str(compiled)
    assert "NP" in compiled.params.values()
    assert "kathmandu" in compiled.params.values()


def test_empty_location():
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    assert load_location_businesses(session, "NP", "Kathmandu") == []


def test_export_limit():
    session = MagicMock()
    session.scalars.return_value.all.return_value = [None, None]
    with (
        patch(f"{MODULE}.MAX_EXPORT_ROWS", 1),
        pytest.raises(PersistenceValidationError),
    ):
        load_location_businesses(session, "NP", "Kathmandu")


@pytest.mark.parametrize("file_format,exporter", [("csv", "csv"), ("xlsx", "excel")])
def test_export_dispatch(file_format, exporter):
    session = MagicMock()
    with (
        patch(f"{MODULE}.load_location_businesses", return_value=[]) as load,
        patch(f"{MODULE}.export_businesses_to_{exporter}") as write,
    ):
        assert (
            export_location(
                session, "NP", "Kathmandu", "output", file_format=file_format
            )
            == 0
        )
        load.assert_called_once_with(session, "NP", "Kathmandu")
        write.assert_called_once_with([], "output")


def test_invalid_format_rejected():
    with pytest.raises(PersistenceValidationError):
        export_location(MagicMock(), "NP", "Kathmandu", "output", file_format="pdf")
