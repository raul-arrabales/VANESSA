from __future__ import annotations

"""Projection helpers for retrieval payloads; canonical contract: docs/services/retrieval_contract.md."""

from typing import Any


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


def project_retrieval_call(retrieval_call: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = retrieval_call.get("results") if isinstance(retrieval_call.get("results"), list) else []
    sources = [serialize_retrieval_source(item) for item in rows if isinstance(item, dict)]
    return sources, serialize_retrieval_summary(retrieval_call, source_count=len(sources))


def normalize_execution_retrieval(execution_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    retrieval_calls = result.get("retrieval_calls") if isinstance(result.get("retrieval_calls"), list) else []
    first_call = retrieval_calls[0] if retrieval_calls and isinstance(retrieval_calls[0], dict) else {}
    return project_retrieval_call(first_call)


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
