from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from .embeddings_service import embed_text_inputs
from .platform_service import resolve_vector_store_adapter
from .platform_types import PlatformControlPlaneError

_SUPPORTED_SCHEMA_PROPERTY_TYPES = {"text", "number", "int", "boolean"}


def ensure_vector_index(database_url: str, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    index_name = _require_index_name(payload.get("index"))
    schema = _normalize_schema(payload.get("schema"))
    adapter = resolve_vector_store_adapter(database_url, config)
    _validate_bound_vector_resource(getattr(adapter, "binding", None), index_name)
    return adapter.ensure_index(index_name=index_name, schema=schema)


def upsert_vector_documents(database_url: str, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    index_name = _require_index_name(payload.get("index"))
    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise PlatformControlPlaneError("invalid_documents", "documents must be a non-empty array", status_code=400)

    normalized_documents = [_normalize_document(document, position=index) for index, document in enumerate(documents)]
    _populate_missing_embeddings(database_url, config, normalized_documents)
    adapter = resolve_vector_store_adapter(database_url, config)
    _validate_bound_vector_resource(getattr(adapter, "binding", None), index_name)
    return adapter.upsert(index_name=index_name, documents=normalized_documents)


def query_vector_documents(database_url: str, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    index_name = _require_index_name(payload.get("index"))
    has_query_text = "query_text" in payload and payload.get("query_text") is not None
    has_embedding = "embedding" in payload and payload.get("embedding") is not None
    if has_query_text == has_embedding:
        raise PlatformControlPlaneError(
            "invalid_query_input",
            "Provide exactly one of query_text or embedding",
            status_code=400,
        )

    query_text = _normalize_query_text(payload.get("query_text")) if has_query_text else None
    embedding = _normalize_embedding(payload.get("embedding"), field_name="embedding") if has_embedding else None
    top_k = _normalize_top_k(payload.get("top_k"))
    filters = _normalize_metadata(payload.get("filters"), field_name="filters")

    if query_text is not None:
        embedding_payload = embed_text_inputs(database_url, config, [query_text])
        embedding = embedding_payload["embeddings"][0]
        query_text = None

    adapter = resolve_vector_store_adapter(database_url, config)
    _validate_bound_vector_resource(getattr(adapter, "binding", None), index_name)
    return adapter.query(
        index_name=index_name,
        query_text=query_text,
        embedding=embedding,
        top_k=top_k,
        filters=filters,
    )


def delete_vector_documents(database_url: str, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    index_name = _require_index_name(payload.get("index"))
    ids = payload.get("ids")
    if not isinstance(ids, list) or not ids:
        raise PlatformControlPlaneError("invalid_ids", "ids must be a non-empty array", status_code=400)

    normalized_ids: list[str] = []
    for index, raw_id in enumerate(ids):
        document_id = str(raw_id).strip()
        if not document_id:
            raise PlatformControlPlaneError(
                "invalid_document_id",
                f"ids[{index}] must be a non-empty string",
                status_code=400,
            )
        normalized_ids.append(document_id)

    adapter = resolve_vector_store_adapter(database_url, config)
    _validate_bound_vector_resource(getattr(adapter, "binding", None), index_name)
    return adapter.delete(index_name=index_name, ids=normalized_ids)


def _require_index_name(value: Any) -> str:
    index_name = str(value or "").strip()
    if not index_name:
        raise PlatformControlPlaneError("invalid_index", "index is required", status_code=400)
    return index_name


def _normalize_schema(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlatformControlPlaneError("invalid_schema", "schema must be an object", status_code=400)

    raw_properties = value.get("properties")
    if raw_properties is None:
        return {}
    if not isinstance(raw_properties, list):
        raise PlatformControlPlaneError("invalid_schema_properties", "schema.properties must be an array", status_code=400)

    properties: list[dict[str, str]] = []
    for index, item in enumerate(raw_properties):
        if not isinstance(item, dict):
            raise PlatformControlPlaneError(
                "invalid_schema_property",
                f"schema.properties[{index}] must be an object",
                status_code=400,
            )
        name = str(item.get("name", "")).strip()
        data_type = str(item.get("data_type", "text")).strip().lower() or "text"
        if not name:
            raise PlatformControlPlaneError(
                "invalid_schema_property_name",
                f"schema.properties[{index}].name is required",
                status_code=400,
            )
        if data_type not in _SUPPORTED_SCHEMA_PROPERTY_TYPES:
            raise PlatformControlPlaneError(
                "invalid_schema_property_type",
                f"schema.properties[{index}].data_type must be one of text, number, int, boolean",
                status_code=400,
            )
        properties.append({"name": name, "data_type": data_type})

    return {"properties": properties}


def _normalize_document(document: Any, *, position: int) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PlatformControlPlaneError(
            "invalid_document",
            f"documents[{position}] must be an object",
            status_code=400,
        )

    document_id = str(document.get("id", "")).strip()
    text = str(document.get("text", "")).strip()
    if not document_id:
        raise PlatformControlPlaneError(
            "invalid_document_id",
            f"documents[{position}].id is required",
            status_code=400,
        )
    if not text:
        raise PlatformControlPlaneError(
            "invalid_document_text",
            f"documents[{position}].text is required",
            status_code=400,
        )

    metadata = _normalize_metadata(document.get("metadata"), field_name=f"documents[{position}].metadata")
    embedding = None
    if "embedding" in document and document.get("embedding") is not None:
        embedding = _normalize_embedding(document.get("embedding"), field_name=f"documents[{position}].embedding")

    normalized = {
        "id": document_id,
        "text": text,
        "metadata": metadata,
    }
    if embedding is not None:
        normalized["embedding"] = embedding
    return normalized


def _populate_missing_embeddings(database_url: str, config: AuthConfig, documents: list[dict[str, Any]]) -> None:
    missing_positions = [index for index, document in enumerate(documents) if document.get("embedding") is None]
    if not missing_positions:
        return
    embedding_payload = embed_text_inputs(
        database_url,
        config,
        [str(documents[index]["text"]) for index in missing_positions],
    )
    embeddings = embedding_payload["embeddings"]
    for offset, document_index in enumerate(missing_positions):
        documents[document_index]["embedding"] = embeddings[offset]


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


def _normalize_embedding(value: Any, *, field_name: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise PlatformControlPlaneError(
            "invalid_embedding",
            f"{field_name} must be a non-empty array of numbers",
            status_code=400,
        )

    normalized: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool):
            raise PlatformControlPlaneError(
                "invalid_embedding_value",
                f"{field_name}[{index}] must be numeric",
                status_code=400,
            )
        try:
            normalized.append(float(item))
        except (TypeError, ValueError) as exc:
            raise PlatformControlPlaneError(
                "invalid_embedding_value",
                f"{field_name}[{index}] must be numeric",
                status_code=400,
            ) from exc
    return normalized


def _validate_bound_vector_resource(binding: Any, index_name: str) -> None:
    if binding is None:
        return
    resource_policy = getattr(binding, "resource_policy", {}) if binding is not None else {}
    selection_mode = str(resource_policy.get("selection_mode") or "explicit").strip().lower()
    if selection_mode == "dynamic_namespace":
        namespace_prefix = str(resource_policy.get("namespace_prefix") or "").strip()
        name_pattern = str(resource_policy.get("name_pattern") or "").strip()
        if namespace_prefix and not index_name.startswith(namespace_prefix):
            raise PlatformControlPlaneError(
                "vector_index_not_allowed",
                "Requested vector index is outside the active deployment namespace",
                status_code=403,
                details={"index": index_name, "namespace_prefix": namespace_prefix},
            )
        if name_pattern:
            import re
            if re.fullmatch(name_pattern, index_name) is None:
                raise PlatformControlPlaneError(
                    "vector_index_not_allowed",
                    "Requested vector index does not match the active deployment naming policy",
                    status_code=403,
                    details={"index": index_name, "name_pattern": name_pattern},
                )
        return

    resources = getattr(binding, "resources", []) if binding is not None else []
    allowed_ids = {
        str(resource.get("provider_resource_id") or resource.get("id") or "").strip()
        for resource in resources
        if isinstance(resource, dict)
    }
    if allowed_ids and index_name in allowed_ids:
        return
    raise PlatformControlPlaneError(
        "vector_index_not_allowed",
        "Requested vector index is not bound by the active deployment",
        status_code=403,
        details={"index": index_name, "allowed_indexes": sorted(item for item in allowed_ids if item)},
    )


def _normalize_metadata(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlatformControlPlaneError(
            "invalid_metadata",
            f"{field_name} must be an object",
            status_code=400,
        )

    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            raise PlatformControlPlaneError(
                "invalid_metadata_key",
                f"{field_name} contains an empty key",
                status_code=400,
            )
        if isinstance(item, bool):
            normalized[normalized_key] = item
            continue
        if isinstance(item, (int, float, str)):
            normalized[normalized_key] = item
            continue
        raise PlatformControlPlaneError(
            "invalid_metadata_value",
            f"{field_name}.{normalized_key} must be a string, number, or boolean",
            status_code=400,
        )
    return normalized
