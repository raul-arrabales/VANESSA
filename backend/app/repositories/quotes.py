from __future__ import annotations

from typing import Any

from ..db import get_connection


QuoteRecord = dict[str, Any]


def list_active_quotes(database_url: str, language: str) -> list[QuoteRecord]:
    normalized = language.strip().lower()
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT id, language, text, author, source_universe, tone, origin
            FROM quotes
            WHERE language = %s
              AND is_active = TRUE
              AND is_approved = TRUE
            ORDER BY id ASC
            """,
            (normalized,),
        ).fetchall()
    return [dict(row) for row in rows]
