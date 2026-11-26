from unittest.mock import Mock

from main import read_search_request
from src.lead_intelligence.models.search_request import (
    SearchRequest,
)


def test_cli_collects_valid_search_request(
    monkeypatch,
):
    mock_input = Mock(
        side_effect=[
            "NP",
            "Kathmandu",
            "Trekking companies",
            "50",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        mock_input,
    )

    request = read_search_request()

    assert isinstance(
        request,
        SearchRequest,
    )

    assert request.country_code == "NP"
    assert request.city == "Kathmandu"
    assert request.query == "Trekking companies"
    assert request.max_results == 50


def test_cli_supports_international_country(
    monkeypatch,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "GB",
                "London",
                "Travel agencies",
                "20",
            ]
        ),
    )

    request = read_search_request()

    assert request.country_code == "GB"

    assert request.city == "London"

    assert request.max_results == 20


def test_cli_uses_default_result_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "NP",
                "Pokhara",
                "Travel agencies",
                "",
            ]
        ),
    )

    request = read_search_request()

    assert request.max_results == 10


def test_cli_retries_after_invalid_country(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "ZZ",
                "Kathmandu",
                "Travel agencies",
                "10",
                "NP",
                "Kathmandu",
                "Travel agencies",
                "10",
            ]
        ),
    )

    request = read_search_request()

    assert request.country_code == "NP"

    output = capsys.readouterr().out

    assert "Invalid search request" in output


def test_cli_retries_after_invalid_result_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "NP",
                "Kathmandu",
                "Travel agencies",
                "101",
                "NP",
                "Kathmandu",
                "Travel agencies",
                "50",
            ]
        ),
    )

    request = read_search_request()

    assert request.max_results == 50


def test_cli_retries_after_non_numeric_result_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "NP",
                "Kathmandu",
                "Travel agencies",
                "invalid",
                "NP",
                "Kathmandu",
                "Travel agencies",
                "25",
            ]
        ),
    )

    request = read_search_request()

    assert request.max_results == 25


def test_cli_retries_after_empty_city(
    monkeypatch,
):
    monkeypatch.setattr(
        "builtins.input",
        Mock(
            side_effect=[
                "NP",
                "",
                "Travel agencies",
                "10",
                "NP",
                "Pokhara",
                "Travel agencies",
                "10",
            ]
        ),
    )

    request = read_search_request()

    assert request.city == "Pokhara"
