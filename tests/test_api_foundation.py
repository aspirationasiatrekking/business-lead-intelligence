from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from src.lead_intelligence.api.app import create_app
from src.lead_intelligence.api.dependencies import build_runtime_engine, get_session


@pytest.fixture
def engine():
    engine = MagicMock(spec=Engine)
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = "bli_app"
    return engine


@pytest.fixture
def client(engine):
    with TestClient(create_app(engine_factory=lambda: engine)) as client:
        yield client


def test_factory_does_not_initialize_engine():
    factory = Mock()
    create_app(engine_factory=factory)
    factory.assert_not_called()


def test_lifespan_owns_engine(engine):
    factory = Mock(return_value=engine)
    with TestClient(create_app(engine_factory=factory)) as client:
        factory.assert_called_once_with()
        assert client.app.state.engine is engine
        engine.dispose.assert_not_called()
    engine.dispose.assert_called_once_with()


def test_health_does_not_query_database(client, engine):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    engine.connect.assert_not_called()


def test_ready_checks_runtime_role(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_rejects_migration_role(client, engine):
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = "bli_migrator"
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("private details"),
        OperationalError(None, None, Exception("secret")),
    ],
)
def test_ready_does_not_expose_database_errors(client, engine, error):
    engine.connect.side_effect = error
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_countries_are_sorted_and_unique(client, engine):
    response = client.get("/api/v1/countries")
    assert response.status_code == 200
    countries = response.json()
    assert {"code": "NP", "name": "Nepal"} in countries
    assert len(countries) >= 240
    assert len({item["code"] for item in countries}) == len(countries)
    assert countries == sorted(countries, key=lambda item: item["name"].casefold())
    engine.connect.assert_not_called()


def test_openapi_exposes_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {
        "/health",
        "/ready",
        "/api/v1/countries",
        "/api/v1/searches/check",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/locations",
        "/api/v1/exports",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
        "/api/v1/auth/change-password",
        "/api/v1/admin/users",
        "/api/v1/admin/users/{user_id}",
        "/api/v1/admin/users/{user_id}/reset-password",
    }


def test_session_dependency_closes_without_committing():
    request = MagicMock()
    session = request.app.state.session_factory.return_value.__enter__.return_value
    dependency = get_session(request)
    assert next(dependency) is session
    dependency.close()
    request.app.state.session_factory.return_value.__exit__.assert_called_once()
    session.commit.assert_not_called()


def test_runtime_engine_uses_restricted_credentials(engine):
    module = "src.lead_intelligence.api.dependencies"
    with (
        patch(f"{module}.DatabaseSettings.load") as load,
        patch(f"{module}.create_database_engine", return_value=engine) as create,
    ):
        load.return_value.username = "bli_app.project_ref"
        assert build_runtime_engine() is engine
        assert load.call_args.args[0].name == ".env"
        create.assert_called_once_with(load.return_value)


def test_runtime_engine_rejects_migration_credentials():
    module = "src.lead_intelligence.api.dependencies"
    with (
        patch(f"{module}.DatabaseSettings.load") as load,
        patch(f"{module}.create_database_engine") as create,
    ):
        load.return_value.username = "bli_migrator.project_ref"
        with pytest.raises(RuntimeError, match="restricted runtime"):
            build_runtime_engine()
        create.assert_not_called()
