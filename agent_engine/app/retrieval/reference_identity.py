from __future__ import annotations

from typing import Any

URI_METADATA_KEYS = ("uri", "file_uri", "source_uri", "url", "source_url")
PATH_METADATA_KEYS = ("source_path", "source_filename", "file_path", "filename")


def group_retrieval_results_for_citations(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for result in results:
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        group_key = reference_group_key(result, metadata)
        if group_key not in groups:
            order.append(group_key)
            groups[group_key] = {
                "title": reference_title(result, metadata),
                "file_reference": reference_file_value(metadata, result),
                "results": [],
            }
        groups[group_key]["results"].append(result)
    return [groups[group_key] for group_key in order]


def reference_group_key(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        first_metadata_string(metadata, URI_METADATA_KEYS),
        first_metadata_string(metadata, PATH_METADATA_KEYS),
        string_or_none(metadata.get("document_id")),
        string_or_none(metadata.get("title")),
        string_or_none(result.get("id")),
    ):
        if value:
            return value
    return "unknown-source"


def reference_title(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        string_or_none(metadata.get("title"))
        or string_or_none(metadata.get("source_display_name"))
        or string_or_none(metadata.get("source_name"))
        or string_or_none(metadata.get("source_filename"))
        or string_or_none(metadata.get("source_path"))
        or string_or_none(result.get("id"))
        or "Source"
    )


def reference_file_value(metadata: dict[str, Any], result: dict[str, Any]) -> str:
    return (
        first_metadata_string(metadata, URI_METADATA_KEYS)
        or first_metadata_string(metadata, PATH_METADATA_KEYS)
        or string_or_none(metadata.get("document_id"))
        or string_or_none(result.get("id"))
        or "Source"
    )


def first_metadata_string(metadata: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        normalized = string_or_none(metadata.get(key))
        if normalized:
            return normalized
    return None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
