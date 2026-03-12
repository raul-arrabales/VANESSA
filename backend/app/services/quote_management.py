from __future__ import annotations

from datetime import date, datetime
from typing import Any


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("invalid_boolean")


def normalize_date(value: str | None) -> date | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("invalid_date") from exc


def normalize_pagination(page_raw: str | None, page_size_raw: str | None) -> tuple[int, int]:
    page = int(page_raw or "1")
    page_size = int(page_size_raw or "10")
    if page < 1:
        raise ValueError("invalid_page")
    if page_size < 1 or page_size > 100:
        raise ValueError("invalid_page_size")
    return page, page_size


def normalize_quote_filters(args: Any) -> dict[str, Any]:
    return {
        "language": str(args.get("language", "")).strip().lower() or None,
        "source_universe": str(args.get("source_universe", "")).strip() or None,
        "tone": str(args.get("tone", "")).strip().lower() or None,
        "origin": str(args.get("origin", "")).strip().lower() or None,
        "is_active": parse_bool(args.get("is_active")),
        "is_approved": parse_bool(args.get("is_approved")),
        "created_from": normalize_date(args.get("created_from")),
        "created_to": normalize_date(args.get("created_to")),
        "query": str(args.get("query", "")).strip() or None,
    }


def normalize_quote_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")

    language = str(payload.get("language", "")).strip().lower()
    text = str(payload.get("text", "")).strip()
    author = str(payload.get("author", "")).strip()
    source_universe = str(payload.get("source_universe", "")).strip()
    tone = str(payload.get("tone", "")).strip().lower()
    origin = str(payload.get("origin", "local")).strip().lower() or "local"
    external_ref = str(payload.get("external_ref", "")).strip() or None

    tags_raw = payload.get("tags", [])
    if not isinstance(tags_raw, list) or not all(isinstance(item, str) for item in tags_raw):
        raise ValueError("invalid_tags")
    tags = [item.strip().lower() for item in tags_raw if item.strip()]

    if not language:
        raise ValueError("invalid_language")
    if not text:
        raise ValueError("invalid_text")
    if not author:
        raise ValueError("invalid_author")
    if not source_universe:
        raise ValueError("invalid_source_universe")
    if not tone:
        raise ValueError("invalid_tone")
    if origin not in {"local", "cloud"}:
        raise ValueError("invalid_origin")

    is_active = payload.get("is_active", True)
    is_approved = payload.get("is_approved", True)
    if not isinstance(is_active, bool):
        raise ValueError("invalid_is_active")
    if not isinstance(is_approved, bool):
        raise ValueError("invalid_is_approved")

    return {
        "language": language,
        "text": text,
        "author": author,
        "source_universe": source_universe,
        "tone": tone,
        "tags": tags,
        "is_active": is_active,
        "is_approved": is_approved,
        "origin": origin,
        "external_ref": external_ref,
    }


def serialize_quote(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "language": row["language"],
        "text": row["text"],
        "author": row["author"],
        "source_universe": row["source_universe"],
        "tone": row["tone"],
        "tags": row.get("tags", []),
        "is_active": bool(row["is_active"]),
        "is_approved": bool(row["is_approved"]),
        "origin": row["origin"],
        "external_ref": row.get("external_ref"),
        "created_at": _serialize_datetime(row.get("created_at")),
        "updated_at": _serialize_datetime(row.get("updated_at")),
    }


def _serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None
