from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.routes import content as content_routes


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, _user_store, config = backend_test_client_factory()
    monkeypatch.setattr(content_routes, "_database_url", lambda: config.database_url)
    monkeypatch.setattr(
        content_routes,
        "resolve_quote_of_the_day",
        lambda _database_url, *, language: {
            "id": 7,
            "text": f"Quote in {language}",
            "author": "VANESSA Curated",
            "source_universe": "Original",
            "tone": "reflective",
            "language": language,
            "date": datetime(2026, 3, 11, tzinfo=timezone.utc).date().isoformat(),
            "origin": "local",
        },
    )
    return test_client


def test_quote_of_the_day_route_is_public_and_uses_requested_language(client) -> None:
    response = client.get("/v1/content/quote-of-the-day?lang=es")

    assert response.status_code == 200
    assert response.get_json() == {
        "quote": {
            "id": 7,
            "text": "Quote in es",
            "author": "VANESSA Curated",
            "source_universe": "Original",
            "tone": "reflective",
            "language": "es",
            "date": "2026-03-11",
            "origin": "local",
        }
    }
