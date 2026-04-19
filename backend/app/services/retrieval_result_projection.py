from __future__ import annotations

"""Projection helpers for retrieval payloads; canonical contract: docs/services/retrieval_contract.md."""

from typing import Any

URI_METADATA_KEYS = ("uri", "file_uri", "source_uri", "url", "source_url")
PATH_METADATA_KEYS = ("source_path", "source_filename", "file_path", "filename")
PAGE_METADATA_KEYS = ("page", "page_number", "page_numbers", "pages")


def trim_retrieval_snippet(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def serialize_retrieval_source(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    text = str(result.get("text", "")).strip()
    title = str(metadata.get("title", "")).strip() or str(result.get("id", "")).strip()
    uri_raw = metadata.get("uri")
    source_type_raw = metadata.get("source_type")
    payload = {
        "id": str(result.get("id", "")).strip(),
        "title": title,
        "snippet": trim_retrieval_snippet(text),
        "uri": string_or_none(uri_raw),
        "source_type": string_or_none(source_type_raw),
        "metadata": metadata,
        "score": result.get("score"),
        "score_kind": result.get("score_kind"),
    }
    if isinstance(result.get("relevance_score"), (int, float)):
        payload["relevance_score"] = float(result["relevance_score"])
    if string_or_none(result.get("relevance_kind")):
        payload["relevance_kind"] = string_or_none(result.get("relevance_kind"))
    raw_components = result.get("relevance_components")
    if isinstance(raw_components, dict):
        components = {
            key: float(value)
            for key, value in raw_components.items()
            if key in {"semantic_score", "keyword_score"} and isinstance(value, (int, float))
        }
        if components:
            payload["relevance_components"] = components
    return payload


def build_retrieval_references(
    results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for result in results:
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        group_key = _reference_group_key(result, metadata)
        if group_key not in grouped:
            order.append(group_key)
            grouped[group_key] = {
                "title": _reference_title(result, metadata),
                "description": _reference_description(result, metadata),
                "uri": _first_metadata_string(metadata, URI_METADATA_KEYS),
                "file_reference": _reference_file_value(metadata, result),
                "pages": set(),
                "source_ids": [],
            }
        grouped[group_key]["source_ids"].append(str(result.get("id", "")).strip())
        grouped[group_key]["pages"].update(_metadata_page_numbers(metadata))

    references: list[dict[str, Any]] = []
    source_reference_lookup: dict[str, dict[str, str]] = {}
    for index, group_key in enumerate(order, start=1):
        group = grouped[group_key]
        reference_id = f"ref-{index}"
        citation_label = f"[{index}]"
        source_ids = [source_id for source_id in group["source_ids"] if source_id]
        reference = {
            "id": reference_id,
            "citation_label": citation_label,
            "title": group["title"],
            "description": group["description"],
            "uri": group["uri"],
            "file_reference": group["file_reference"],
            "pages": sorted(group["pages"]),
            "source_ids": source_ids,
        }
        references.append(reference)
        for source_id in source_ids:
            source_reference_lookup[source_id] = {
                "reference_id": reference_id,
                "citation_label": citation_label,
            }
    return references, source_reference_lookup


def serialize_retrieval_summary(
    retrieval_call: dict[str, Any],
    *,
    source_count: int | None = None,
) -> dict[str, Any]:
    retrieval = {
        "index": str(retrieval_call.get("index", "")).strip(),
        "result_count": int(retrieval_call.get("result_count", source_count or 0) or 0),
    }
    if string_or_none(retrieval_call.get("search_method")):
        retrieval["search_method"] = str(retrieval_call["search_method"]).strip()
    if string_or_none(retrieval_call.get("query_preprocessing")):
        retrieval["query_preprocessing"] = str(retrieval_call["query_preprocessing"]).strip()
    if isinstance(retrieval_call.get("top_k"), int):
        retrieval["top_k"] = int(retrieval_call["top_k"])
    if isinstance(retrieval_call.get("hybrid_alpha"), (int, float)):
        retrieval["hybrid_alpha"] = float(retrieval_call["hybrid_alpha"])
    return retrieval


def project_retrieval_call(
    retrieval_call: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    rows = retrieval_call.get("results") if isinstance(retrieval_call.get("results"), list) else []
    result_rows = [item for item in rows if isinstance(item, dict)]
    references, reference_lookup = build_retrieval_references(result_rows)
    sources = []
    for item in result_rows:
        source = serialize_retrieval_source(item)
        source_reference = reference_lookup.get(source["id"])
        if source_reference:
            source.update(source_reference)
        sources.append(source)
    return sources, serialize_retrieval_summary(retrieval_call, source_count=len(sources)), references


def normalize_execution_retrieval(
    execution_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    result = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    retrieval_calls = result.get("retrieval_calls") if isinstance(result.get("retrieval_calls"), list) else []
    first_call = retrieval_calls[0] if retrieval_calls and isinstance(retrieval_calls[0], dict) else {}
    return project_retrieval_call(first_call)


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _first_metadata_string(metadata: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        normalized = string_or_none(metadata.get(key))
        if normalized:
            return normalized
    return None


def _reference_group_key(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        _first_metadata_string(metadata, URI_METADATA_KEYS),
        _first_metadata_string(metadata, PATH_METADATA_KEYS),
        string_or_none(metadata.get("document_id")),
        string_or_none(metadata.get("title")),
        string_or_none(result.get("id")),
    ):
        if value:
            return value
    return "unknown-source"


def _reference_title(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        string_or_none(metadata.get("title"))
        or string_or_none(metadata.get("source_display_name"))
        or string_or_none(metadata.get("source_name"))
        or string_or_none(metadata.get("source_filename"))
        or string_or_none(metadata.get("source_path"))
        or string_or_none(result.get("id"))
        or "Source"
    )


def _reference_description(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        string_or_none(metadata.get("description"))
        or string_or_none(metadata.get("source_description"))
        or string_or_none(metadata.get("source_display_name"))
        or string_or_none(metadata.get("source_name"))
        or string_or_none(metadata.get("source_type"))
        or _reference_title(result, metadata)
    )


def _reference_file_value(metadata: dict[str, Any], result: dict[str, Any]) -> str | None:
    return (
        _first_metadata_string(metadata, URI_METADATA_KEYS)
        or _first_metadata_string(metadata, PATH_METADATA_KEYS)
        or string_or_none(metadata.get("document_id"))
        or string_or_none(result.get("id"))
    )


def _metadata_page_numbers(metadata: dict[str, Any]) -> set[int]:
    pages: set[int] = set()
    for key in PAGE_METADATA_KEYS:
        pages.update(_coerce_page_numbers(metadata.get(key)))

    start = _first_page_number(metadata.get("page_start"))
    end = _first_page_number(metadata.get("page_end"))
    if start is not None and end is not None:
        lower = min(start, end)
        upper = max(start, end)
        if upper - lower <= 50:
            pages.update(range(lower, upper + 1))
        else:
            pages.update({lower, upper})
    elif start is not None:
        pages.add(start)
    elif end is not None:
        pages.add(end)

    return pages


def _coerce_page_numbers(value: Any) -> set[int]:
    if value is None or isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value} if value > 0 else set()
    if isinstance(value, float):
        return {int(value)} if value.is_integer() and value > 0 else set()
    if isinstance(value, str):
        pages: set[int] = set()
        for part in value.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_raw, end_raw = part.split("-", 1)
                start = _parse_positive_int(start_raw)
                end = _parse_positive_int(end_raw)
                if start is not None and end is not None:
                    lower = min(start, end)
                    upper = max(start, end)
                    if upper - lower <= 50:
                        pages.update(range(lower, upper + 1))
                    else:
                        pages.update({lower, upper})
                continue
            page = _parse_positive_int(part)
            if page is not None:
                pages.add(page)
        return pages
    if isinstance(value, list):
        pages: set[int] = set()
        for item in value:
            pages.update(_coerce_page_numbers(item))
        return pages
    return set()


def _first_page_number(value: Any) -> int | None:
    pages = _coerce_page_numbers(value)
    return min(pages) if pages else None


def _parse_positive_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and value > 0 else None
    normalized = str(value).strip()
    if not normalized.isdigit():
        return None
    parsed = int(normalized)
    return parsed if parsed > 0 else None
