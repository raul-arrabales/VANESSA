from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

import psycopg

from ..db import get_connection

QuoteRecord = dict[str, Any]


def _build_where_clause(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    language = filters.get("language")
    if language:
        clauses.append("language = %s")
        params.append(language)

    source_universe = filters.get("source_universe")
    if source_universe:
        clauses.append("source_universe ILIKE %s")
        params.append(f"%{source_universe}%")

    tone = filters.get("tone")
    if tone:
        clauses.append("tone = %s")
        params.append(tone)

    origin = filters.get("origin")
    if origin:
        clauses.append("origin = %s")
        params.append(origin)

    is_active = filters.get("is_active")
    if is_active is not None:
        clauses.append("is_active = %s")
        params.append(is_active)

    is_approved = filters.get("is_approved")
    if is_approved is not None:
        clauses.append("is_approved = %s")
        params.append(is_approved)

    created_from = filters.get("created_from")
    if created_from:
        clauses.append("created_at >= %s")
        params.append(datetime.combine(created_from, time.min, tzinfo=timezone.utc))

    created_to = filters.get("created_to")
    if created_to:
        clauses.append("created_at <= %s")
        params.append(datetime.combine(created_to, time.max, tzinfo=timezone.utc))

    query = filters.get("query")
    if query:
        clauses.append("(text ILIKE %s OR author ILIKE %s OR source_universe ILIKE %s)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

    if not clauses:
        return "", params

    return f"WHERE {' AND '.join(clauses)}", params


def get_quote_summary(database_url: str) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_active = TRUE) AS active,
                    COUNT(*) FILTER (WHERE is_approved = TRUE) AS approved
                FROM quotes
                """
            )
            totals = cursor.fetchone() or {"total": 0, "active": 0, "approved": 0}

            grouped_counts: dict[str, list[dict[str, Any]]] = {}
            for group_name, column in [
                ("by_language", "language"),
                ("by_tone", "tone"),
                ("by_origin", "origin"),
            ]:
                cursor.execute(
                    f"""
                    SELECT {column} AS value, COUNT(*) AS count
                    FROM quotes
                    GROUP BY {column}
                    ORDER BY COUNT(*) DESC, {column} ASC
                    """
                )
                grouped_counts[group_name] = [dict(row) for row in cursor.fetchall()]

    return {
        "total": int(totals["total"]),
        "active": int(totals["active"]),
        "approved": int(totals["approved"]),
        **grouped_counts,
    }


def list_quotes(
    database_url: str,
    *,
    filters: dict[str, Any],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    where_clause, params = _build_where_clause(filters)
    offset = (page - 1) * page_size

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM quotes {where_clause}",
                params,
            )
            total = int((cursor.fetchone() or {"total": 0})["total"])

            cursor.execute(
                f"""
                SELECT
                    id,
                    language,
                    text,
                    author,
                    source_universe,
                    tone,
                    tags,
                    is_active,
                    is_approved,
                    origin,
                    external_ref,
                    created_at,
                    updated_at
                FROM quotes
                {where_clause}
                ORDER BY updated_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            items = [dict(row) for row in cursor.fetchall()]

    return {"items": items, "total": total}


def get_quote_by_id(database_url: str, quote_id: int) -> QuoteRecord | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                language,
                text,
                author,
                source_universe,
                tone,
                tags,
                is_active,
                is_approved,
                origin,
                external_ref,
                created_at,
                updated_at
            FROM quotes
            WHERE id = %s
            """,
            (quote_id,),
        ).fetchone()
    return dict(row) if row else None


def create_quote(database_url: str, *, payload: dict[str, Any]) -> QuoteRecord:
    now = datetime.now(tz=timezone.utc)
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO quotes (
                    language,
                    text,
                    author,
                    source_universe,
                    tone,
                    tags,
                    is_active,
                    is_approved,
                    origin,
                    external_ref,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    language,
                    text,
                    author,
                    source_universe,
                    tone,
                    tags,
                    is_active,
                    is_approved,
                    origin,
                    external_ref,
                    created_at,
                    updated_at
                """,
                (
                    payload["language"],
                    payload["text"],
                    payload["author"],
                    payload["source_universe"],
                    payload["tone"],
                    psycopg.types.json.Jsonb(payload["tags"]),
                    payload["is_active"],
                    payload["is_approved"],
                    payload["origin"],
                    payload["external_ref"],
                    now,
                    now,
                ),
            )
            row = cursor.fetchone()
    if row is None:
        raise ValueError("quote_create_failed")
    return dict(row)


def update_quote(database_url: str, *, quote_id: int, payload: dict[str, Any]) -> QuoteRecord | None:
    now = datetime.now(tz=timezone.utc)
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE quotes
                SET
                    language = %s,
                    text = %s,
                    author = %s,
                    source_universe = %s,
                    tone = %s,
                    tags = %s::jsonb,
                    is_active = %s,
                    is_approved = %s,
                    origin = %s,
                    external_ref = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING
                    id,
                    language,
                    text,
                    author,
                    source_universe,
                    tone,
                    tags,
                    is_active,
                    is_approved,
                    origin,
                    external_ref,
                    created_at,
                    updated_at
                """,
                (
                    payload["language"],
                    payload["text"],
                    payload["author"],
                    payload["source_universe"],
                    payload["tone"],
                    psycopg.types.json.Jsonb(payload["tags"]),
                    payload["is_active"],
                    payload["is_approved"],
                    payload["origin"],
                    payload["external_ref"],
                    now,
                    quote_id,
                ),
            )
            row = cursor.fetchone()
    return dict(row) if row else None
