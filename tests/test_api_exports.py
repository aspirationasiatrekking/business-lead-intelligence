from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from src.lead_intelligence.api.app import create_app
from src.lead_intelligence.api.auth import require_user
from src.lead_intelligence.api.dependencies import get_session
from src.lead_intelligence.auth.service import Principal
from src.lead_intelligence.database.exceptions import PersistenceValidationError

MODULE = "src.lead_intelligence.api.exports"


@pytest.fixture
def api():
    session = MagicMock()
    app = create_app(engine_factory=MagicMock())
    app.dependency_overrides[get_session] = lambda: session
    principal = Principal(uuid4(), "employee", "Employee", "employee", False)
    app.dependency_overrides[require_user] = lambda: principal
    with TestClient(app) as client:
        yield client, session


def test_locations_grouped_and_paginated(api):
    client, session = api
    session.execute.return_value.all.return_value = [
        ("NP", "Kathmandu", 5),
        ("NP", "Pokhara", 2),
    ]
    response = client.get("/api/v1/locations?country_code=np&limit=1")
    assert response.status_code == 200
    assert response.json() == {
        "items": [{"country_code": "NP", "city": "Kathmandu", "business_count": 5}],
        "limit": 1,
        "offset": 0,
        "has_more": True,
    }
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect())).lower()
    assert "count(distinct" in sql
    assert "group by" in sql
    assert "city_normalized" in sql
    assert "search_jobs.status" in sql
    assert "NP" in statement.compile().params.values()


def test_locations_empty(api):
    client, session = api
    session.execute.return_value.all.return_value = []
    assert client.get("/api/v1/locations").json()["items"] == []


@pytest.mark.parametrize("query", ["country_code=ZZ", "limit=0", "offset=-1"])
def test_invalid_locations(api, query):
    client, session = api
    assert client.get(f"/api/v1/locations?{query}").status_code == 422
    session.execute.assert_not_called()


@pytest.mark.parametrize(
    "file_format,media",
    [
        ("csv", "text/csv"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_download_and_cleanup(api, file_format, media):
    client, session = api
    paths = []

    def fake_export(db, country, city, output_path, *, file_format):
        assert db is session
        assert (country, city) == ("NP", "Kathmandu")
        path = Path(output_path)
        paths.append(path)
        path.write_bytes(b"example file")
        return 0

    with patch(f"{MODULE}.export_location", side_effect=fake_export):
        response = client.get(
            "/api/v1/exports",
            params={"country_code": "np", "city": " Kathmandu ", "format": file_format},
        )
    assert response.status_code == 200
    assert response.content == b"example file"
    assert response.headers["content-type"].startswith(media)
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="leads-NP.{file_format}"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert not paths[0].parent.exists()


@pytest.mark.parametrize(
    "params",
    [
        {"country_code": "ZZ", "city": "Kathmandu"},
        {"country_code": "NP", "city": " "},
        {"country_code": "NP", "city": "Kathmandu", "format": "pdf"},
    ],
)
def test_invalid_export(api, params):
    client, _ = api
    with patch(f"{MODULE}.export_location") as exporter:
        assert client.get("/api/v1/exports", params=params).status_code == 422
        exporter.assert_not_called()


def test_export_limit_cleanup(api):
    client, _ = api
    paths = []

    def fail(*args, **kwargs):
        path = Path(args[3])
        paths.append(path)
        path.write_bytes(b"partial")
        raise PersistenceValidationError("Location exceeds maximum export size.")

    with patch(f"{MODULE}.export_location", side_effect=fail):
        response = client.get("/api/v1/exports?country_code=NP&city=Kathmandu")
    assert response.status_code == 422
    assert not paths[0].parent.exists()
