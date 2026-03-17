from __future__ import annotations

from datetime import datetime, timezone

from app.services import quote_service


def _quote_template(quote_id: int, *, language: str = "en", text: str | None = None) -> dict[str, object]:
    return {
        "id": quote_id,
        "text": text or f"Quote {quote_id}",
        "author": "VANESSA Curated",
        "source_universe": "Original",
        "tone": "reflective",
        "language": language,
        "origin": "local",
    }


def test_select_quote_for_day_is_deterministic() -> None:
    quotes = [_quote_template(1), _quote_template(2), _quote_template(3)]
    selected_date = datetime(2026, 3, 11, tzinfo=timezone.utc).date()

    first = quote_service.select_quote_for_day(quotes, language="en", selected_date=selected_date)
    second = quote_service.select_quote_for_day(quotes, language="en", selected_date=selected_date)

    assert first == second
    assert first["date"] == "2026-03-11"


def test_select_quote_for_day_changes_with_date_when_pool_allows() -> None:
    quotes = [_quote_template(1), _quote_template(2), _quote_template(3), _quote_template(4)]

    first = quote_service.select_quote_for_day(
        quotes,
        language="en",
        selected_date=datetime(2026, 3, 11, tzinfo=timezone.utc).date(),
    )
    second = quote_service.select_quote_for_day(
        quotes,
        language="en",
        selected_date=datetime(2026, 3, 12, tzinfo=timezone.utc).date(),
    )

    assert first["id"] != second["id"]


def test_select_random_quote_uses_random_choice(monkeypatch) -> None:
    quotes = [_quote_template(1), _quote_template(2), _quote_template(3)]
    monkeypatch.setattr(quote_service.random, "choice", lambda rows: rows[-1])

    selected = quote_service.select_random_quote(
        quotes,
        selected_date=datetime(2026, 3, 11, tzinfo=timezone.utc).date(),
    )

    assert selected["id"] == 3
    assert selected["date"] == "2026-03-11"


def test_resolve_quote_of_the_day_falls_back_to_default_language(monkeypatch) -> None:
    quote_rows = [_quote_template(9, language="en", text="English only")]

    def fake_list_active_quotes(_database_url: str, language: str) -> list[dict[str, object]]:
        return quote_rows if language == "en" else []

    monkeypatch.setattr(quote_service, "list_active_quotes", fake_list_active_quotes)

    resolved = quote_service.resolve_quote_of_the_day(
        "postgresql://ignored",
        language="es",
        now=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )

    assert resolved["text"] == "English only"
    assert resolved["language"] == "en"


def test_resolve_quote_of_the_day_supports_random_selection(monkeypatch) -> None:
    quote_rows = [
        _quote_template(1, language="en", text="First"),
        _quote_template(2, language="en", text="Second"),
    ]

    monkeypatch.setattr(quote_service, "list_active_quotes", lambda *_args, **_kwargs: quote_rows)
    monkeypatch.setattr(quote_service.random, "choice", lambda rows: rows[1])

    resolved = quote_service.resolve_quote_of_the_day(
        "postgresql://ignored",
        language="en",
        selection_mode="random",
        now=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )

    assert resolved["id"] == 2
    assert resolved["text"] == "Second"
    assert resolved["date"] == "2026-03-11"


def test_resolve_quote_of_the_day_returns_code_fallback_when_store_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(quote_service, "list_active_quotes", lambda *_args, **_kwargs: [])

    resolved = quote_service.resolve_quote_of_the_day(
        "postgresql://ignored",
        language="es",
        now=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )

    assert resolved["id"] == 0
    assert resolved["language"] == "es"
    assert resolved["date"] == "2026-03-11"
