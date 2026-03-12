from __future__ import annotations

from datetime import datetime, time, timezone

import psycopg

from ..db import get_connection
from ..services.quote_management_types import (
    QuoteCountBucket,
    QuoteFilters,
    QuoteListResult,
    QuotePayload,
    QuoteRecord,
    QuoteSummary,
)


def _build_where_clause(filters: QuoteFilters) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if filters.language:
        clauses.append("language = %s")
        params.append(filters.language)

    if filters.source_universe:
        clauses.append("source_universe ILIKE %s")
        params.append(f"%{filters.source_universe}%")

    if filters.tone:
        clauses.append("tone = %s")
        params.append(filters.tone)

    if filters.origin:
        clauses.append("origin = %s")
        params.append(filters.origin)

    if filters.is_active is not None:
        clauses.append("is_active = %s")
        params.append(filters.is_active)

    if filters.is_approved is not None:
        clauses.append("is_approved = %s")
        params.append(filters.is_approved)

    if filters.created_from:
        clauses.append("created_at >= %s")
        params.append(datetime.combine(filters.created_from, time.min, tzinfo=timezone.utc))

    if filters.created_to:
        clauses.append("created_at <= %s")
        params.append(datetime.combine(filters.created_to, time.max, tzinfo=timezone.utc))

    if filters.query:
        clauses.append("(text ILIKE %s OR author ILIKE %s OR source_universe ILIKE %s)")
        params.extend([f"%{filters.query}%", f"%{filters.query}%", f"%{filters.query}%"])

    if not clauses:
        return "", params

    return f"WHERE {' AND '.join(clauses)}", params


def get_quote_summary(database_url: str) -> QuoteSummary:
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

            grouped_counts: dict[str, list[QuoteCountBucket]] = {}
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
                grouped_counts[group_name] = [
                    QuoteCountBucket(value=str(row["value"]), count=int(row["count"]))
                    for row in cursor.fetchall()
                ]

    return QuoteSummary(
        total=int(totals["total"]),
        active=int(totals["active"]),
        approved=int(totals["approved"]),
        by_language=grouped_counts["by_language"],
        by_tone=grouped_counts["by_tone"],
        by_origin=grouped_counts["by_origin"],
    )


def list_quotes(
    database_url: str,
    *,
    filters: QuoteFilters,
    page: int,
    page_size: int,
) -> QuoteListResult:
    where_clause, params = _build_where_clause(filters)
    offset = (page - 1) * page_size

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM quotes {where_clause}", params)
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
            items = [_row_to_record(row) for row in cursor.fetchall()]

    return QuoteListResult(items=items, total=total)


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
    return _row_to_record(row) if row else None


def create_quote(database_url: str, *, payload: QuotePayload) -> QuoteRecord:
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
                    payload.language,
                    payload.text,
                    payload.author,
                    payload.source_universe,
                    payload.tone,
                    psycopg.types.json.Jsonb(payload.tags),
                    payload.is_active,
                    payload.is_approved,
                    payload.origin,
                    payload.external_ref,
                    now,
                    now,
                ),
            )
            row = cursor.fetchone()
    if row is None:
        raise ValueError("quote_create_failed")
    return _row_to_record(row)


def update_quote(database_url: str, *, quote_id: int, payload: QuotePayload) -> QuoteRecord | None:
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
                    payload.language,
                    payload.text,
                    payload.author,
                    payload.source_universe,
                    payload.tone,
                    psycopg.types.json.Jsonb(payload.tags),
                    payload.is_active,
                    payload.is_approved,
                    payload.origin,
                    payload.external_ref,
                    now,
                    quote_id,
                ),
            )
            row = cursor.fetchone()
    return _row_to_record(row) if row else None


def _row_to_record(row: dict[str, object]) -> QuoteRecord:
    return QuoteRecord(
        id=int(row["id"]),
        language=str(row["language"]),
        text=str(row["text"]),
        author=str(row["author"]),
        source_universe=str(row["source_universe"]),
        tone=str(row["tone"]),
        tags=list(row.get("tags", [])),
        is_active=bool(row["is_active"]),
        is_approved=bool(row["is_approved"]),
        origin=str(row["origin"]),
        external_ref=row.get("external_ref") if isinstance(row.get("external_ref"), str) or row.get("external_ref") is None else str(row.get("external_ref")),
        created_at=row.get("created_at") if isinstance(row.get("created_at"), datetime) or row.get("created_at") is None else None,
        updated_at=row.get("updated_at") if isinstance(row.get("updated_at"), datetime) or row.get("updated_at") is None else None,
    )
