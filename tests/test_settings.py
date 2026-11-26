from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from src.lead_intelligence.search.serper_provider import (
    SerperResponseError,
    SerperSearchProvider,
)
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.settings import ApplicationSettings


def test_explicit_file_and_environment_precedence(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("SERPER_API_KEY=file-key\nSERPER_TIMEOUT_SECONDS=12\n")
    monkeypatch.setenv("SERPER_API_KEY", "env-key")
    monkeypatch.delenv("SERPER_TIMEOUT_SECONDS", raising=False)
    settings = ApplicationSettings.load(path)
    assert settings.serper_api_key == "env-key"
    assert settings.serper_timeout == 12
    assert "env-key" not in repr(settings)
    assert ApplicationSettings.load().serper_timeout == 30


@pytest.mark.parametrize("value", ["0", "31", "nan", "-1", "1.5"])
def test_invalid_timeout(monkeypatch, value):
    monkeypatch.setenv("SERPER_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError):
        ApplicationSettings.load()


def test_invalid_key_is_not_disclosed():
    with pytest.raises(ValueError, match="SERPER_API_KEY is invalid") as exc:
        ApplicationSettings(serper_api_key="secret\nvalue")
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_provider_rejects_redirect_without_retry(monkeypatch, status):
    settings = ApplicationSettings(serper_api_key="test-key", serper_timeout=9)
    provider = SerperSearchProvider(settings)
    response = requests.Response()
    response.status_code = status
    response.headers["Location"] = "https://example.com"
    response._content = b""
    response._content_consumed = True
    post = Mock(return_value=response)
    monkeypatch.setattr(provider.session, "post", post)
    try:
        with pytest.raises(SerperResponseError, match="redirect"):
            provider.search_places("Travel agencies")
        post.assert_called_once()
        assert post.call_args.kwargs["allow_redirects"] is False
        assert post.call_args.kwargs["timeout"] == 9
        assert provider.session.trust_env is False
    finally:
        provider.close()


def test_service_limits():
    settings = ApplicationSettings(max_search_pages=3, max_contact_pages=0)
    search = BusinessSearchService(provider=Mock(), settings=settings)
    assert search.MAX_SEARCH_PAGES == 3
    assert ContactDiscoveryService(settings).MAX_CONTACT_PAGES == 0
    assert settings.output_dir == Path("output")
