from __future__ import annotations

"""Projection helpers for retrieval payloads; canonical contract: docs/services/retrieval_contract.md."""

from typing import Any
from urllib.parse import quote

from .retrieval_reference_identity import (
    first_metadata_string,
    metadata_page_numbers,
    reference_description,
    reference_file_value,
    reference_group_key,
    reference_title,
    string_or_none,
    URI_METADATA_KEYS,
)


def trim_retrieval_snippet(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def source_file_url_from_metadata(metadata: dict[str, Any]) -> str | None:
    knowledge_base_id = string_or_none(metadata.get("knowledge_base_id"))
    document_id = string_or_none(metadata.get("document_id"))
    source_path = string_or_none(metadata.get("source_path"))
    source_type = str(metadata.get("source_type") or "").strip().lower()
    is_source_managed = bool(metadata.get("managed_by_source")) or bool(string_or_none(metadata.get("source_id")))
    if source_type == "local_directory":
        is_source_managed = True
    if not knowledge_base_id or not document_id or not source_path or not is_source_managed:
        return None
    return (
        "/v1/playgrounds/knowledge-bases/"
        f"{quote(knowledge_base_id, safe='')}/documents/{quote(document_id, safe='')}/source-file"
    )


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
    file_url = source_file_url_from_metadata(metadata)
    if file_url:
        payload["file_url"] = file_url
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
        group_key = reference_group_key(result, metadata)
        if group_key not in grouped:
            order.append(group_key)
            grouped[group_key] = {
                "title": reference_title(result, metadata),
                "description": reference_description(result, metadata),
                "uri": first_metadata_string(metadata, URI_METADATA_KEYS),
                "file_reference": reference_file_value(metadata, result),
                "file_url": source_file_url_from_metadata(metadata),
                "pages": set(),
                "source_ids": [],
            }
        if not grouped[group_key].get("file_url"):
            grouped[group_key]["file_url"] = source_file_url_from_metadata(metadata)
        grouped[group_key]["source_ids"].append(str(result.get("id", "")).strip())
        grouped[group_key]["pages"].update(metadata_page_numbers(metadata))

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
            **({"file_url": group["file_url"]} if group.get("file_url") else {}),
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
