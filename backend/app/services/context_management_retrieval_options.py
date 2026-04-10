from __future__ import annotations

import re
from typing import Any

from .context_management_serialization import _normalize_schema
from .context_management_retrieval_types import KnowledgeBaseRetrievalOptions
from .platform_types import PlatformControlPlaneError


def _normalize_query_text(value: Any) -> str:
    query_text = str(value or "").strip()
    if not query_text:
        raise PlatformControlPlaneError("invalid_query_text", "query_text must be a non-empty string", status_code=400)
    return query_text


def _normalize_top_k(value: Any) -> int:
    if value is None:
        return 5
    if isinstance(value, bool):
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400) from exc
    if top_k <= 0:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    return top_k


def _normalize_search_method(value: Any) -> str:
    normalized = str(value or "semantic").strip().lower() or "semantic"
    if normalized not in {"semantic", "keyword", "hybrid"}:
        raise PlatformControlPlaneError(
            "invalid_search_method",
            "search_method must be one of semantic, keyword, or hybrid",
            status_code=400,
        )
    return normalized


def _normalize_query_preprocessing(value: Any) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    if normalized not in {"none", "normalize"}:
        raise PlatformControlPlaneError(
            "invalid_query_preprocessing",
            "query_preprocessing must be one of none or normalize",
            status_code=400,
        )
    return normalized


def _normalize_hybrid_alpha(value: Any) -> float:
    if value in {None, ""}:
        return 0.5
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError(
            "invalid_hybrid_alpha",
            "hybrid_alpha must be a number between 0.0 and 1.0",
            status_code=400,
        ) from exc
    if normalized < 0.0 or normalized > 1.0:
        raise PlatformControlPlaneError(
            "invalid_hybrid_alpha",
            "hybrid_alpha must be between 0.0 and 1.0",
            status_code=400,
        )
    return normalized


def _coerce_filter_value(
    value: Any,
    *,
    property_type: str,
    field_name: str,
) -> str | int | float | bool:
    normalized_type = property_type.strip().lower()
    if normalized_type == "text":
        if isinstance(value, (dict, list)):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a string", status_code=400)
        return str(value)
    if normalized_type == "number":
        if isinstance(value, bool):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            try:
                return float(stripped)
            except ValueError as exc:
                raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400) from exc
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400)
    if normalized_type == "int":
        if isinstance(value, bool):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be an integer", status_code=400)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if re.fullmatch(r"-?\d+", stripped):
                return int(stripped)
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be an integer", status_code=400)
    if normalized_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            stripped = value.strip().lower()
            if stripped == "true":
                return True
            if stripped == "false":
                return False
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be true or false", status_code=400)
    raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} has an unsupported metadata type", status_code=400)


def _normalize_filters(
    value: Any,
    *,
    knowledge_base_schema: dict[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlatformControlPlaneError("invalid_filters", "filters must be an object", status_code=400)
    normalized_schema = _normalize_schema(knowledge_base_schema or {})
    schema_properties = {
        str(item.get("name") or "").strip(): str(item.get("data_type") or "text").strip().lower() or "text"
        for item in list(normalized_schema.get("properties") or [])
    }
    normalized: dict[str, Any] = {}
    for key, item_value in value.items():
        property_name = str(key or "").strip()
        property_type = schema_properties.get(property_name)
        if not property_name or property_type is None:
            raise PlatformControlPlaneError(
                "invalid_metadata_key",
                f"filters key '{property_name or key}' is not defined in the knowledge-base schema",
                status_code=400,
            )
        normalized[property_name] = _coerce_filter_value(
            item_value,
            property_type=property_type,
            field_name=f"filters.{property_name}",
        )
    return normalized


def normalize_knowledge_base_retrieval_options(
    payload: dict[str, Any],
    *,
    knowledge_base_schema: dict[str, Any] | None = None,
) -> KnowledgeBaseRetrievalOptions:
    query_text = _normalize_query_text(payload.get("query_text"))
    top_k = _normalize_top_k(payload.get("top_k"))
    search_method = _normalize_search_method(payload.get("search_method"))
    query_preprocessing = _normalize_query_preprocessing(payload.get("query_preprocessing"))
    hybrid_alpha = _normalize_hybrid_alpha(payload.get("hybrid_alpha")) if search_method == "hybrid" else None
    filters = _normalize_filters(payload.get("filters"), knowledge_base_schema=knowledge_base_schema)
    return KnowledgeBaseRetrievalOptions(
        query_text=query_text,
        top_k=top_k,
        search_method=search_method,  # type: ignore[arg-type]
        query_preprocessing=query_preprocessing,  # type: ignore[arg-type]
        hybrid_alpha=hybrid_alpha,
        filters=filters,
    )
