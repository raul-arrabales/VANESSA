from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
from typing import Any

from ..repositories.quotes import list_active_quotes

DEFAULT_LANGUAGE = "en"

_FALLBACK_QUOTES: dict[str, dict[str, str]] = {
    "en": {
        "text": "Even in deep space, wisdom still needs a human hand on the console.",
        "author": "VANESSA",
        "source_universe": "Original",
        "tone": "reflective",
        "origin": "local",
    },
    "es": {
        "text": "Incluso en el espacio profundo, la sabiduria todavia necesita una mano humana en la consola.",
        "author": "VANESSA",
        "source_universe": "Original",
        "tone": "reflective",
        "origin": "local",
    },
}


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = language.strip().lower()
    if not normalized:
        return DEFAULT_LANGUAGE
    return normalized.split("-")[0]


def _date_key(selected_date: date) -> str:
    return selected_date.isoformat()


def select_quote_for_day(quotes: list[dict[str, Any]], *, language: str, selected_date: date) -> dict[str, Any]:
    if not quotes:
        raise ValueError("quotes are required")

    seed = f"{normalize_language(language)}:{_date_key(selected_date)}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()
    index = int(digest[:8], 16) % len(quotes)
    selected = dict(quotes[index])
    selected["date"] = _date_key(selected_date)
    return selected


def fallback_quote(*, language: str, selected_date: date) -> dict[str, Any]:
    normalized = normalize_language(language)
    template = _FALLBACK_QUOTES.get(normalized, _FALLBACK_QUOTES[DEFAULT_LANGUAGE])
    return {
        "id": 0,
        "text": template["text"],
        "author": template["author"],
        "source_universe": template["source_universe"],
        "tone": template["tone"],
        "language": normalized if normalized in _FALLBACK_QUOTES else DEFAULT_LANGUAGE,
        "date": _date_key(selected_date),
        "origin": template["origin"],
    }


def resolve_quote_of_the_day(
    database_url: str,
    *,
    language: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized = normalize_language(language)
    selected_date = (now or datetime.now(tz=timezone.utc)).date()

    requested_quotes = list_active_quotes(database_url, normalized)
    if requested_quotes:
        return select_quote_for_day(requested_quotes, language=normalized, selected_date=selected_date)

    if normalized != DEFAULT_LANGUAGE:
        default_quotes = list_active_quotes(database_url, DEFAULT_LANGUAGE)
        if default_quotes:
            return select_quote_for_day(default_quotes, language=DEFAULT_LANGUAGE, selected_date=selected_date)

    return fallback_quote(language=normalized, selected_date=selected_date)
