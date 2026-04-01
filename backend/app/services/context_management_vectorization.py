from __future__ import annotations

from typing import Any

from ..repositories import platform_control_plane as platform_repo
from .context_management_chunking_compatibility import (
    resolve_embedding_resource_chunking_constraints,
    serialize_embeddings_chunking_constraints,
)
from .platform_serialization import _runtime_identifier_for_resource
from .platform_types import CAPABILITY_EMBEDDINGS, CAPABILITY_VECTOR_STORE, PlatformControlPlaneError

VECTOR_MODE_VANESSA_EMBEDDINGS = "vanessa_embeddings"
VECTOR_MODE_SELF_PROVIDED = "self_provided"
SUPPORTED_KB_VECTORIZATION_MODES = {VECTOR_MODE_VANESSA_EMBEDDINGS, VECTOR_MODE_SELF_PROVIDED}


def _provider_supports_named_vectors(provider_key: str) -> bool:
    return provider_key.strip().lower() == "weaviate_local"


def _serialize_provider_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    provider_id = str(row.get("id") or row.get("provider_instance_id") or "").strip()
    if not provider_id:
        return None
    return {
        "id": provider_id,
        "slug": str(row.get("slug") or row.get("provider_slug") or "").strip() or None,
        "provider_key": str(row.get("provider_key") or "").strip().lower() or None,
        "display_name": str(row.get("display_name") or row.get("provider_display_name") or "").strip() or None,
        "enabled": row.get("enabled") if row.get("enabled") is not None else None,
        "capability": str(row.get("capability_key") or row.get("capability") or "").strip().lower() or None,
    }


def _normalize_embedding_resource(resource: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(resource, dict):
        return None
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    resource_id = str(resource.get("provider_resource_id") or resource.get("id") or "").strip()
    if not resource_id:
        return None
    normalized = {
        "id": resource_id,
        "provider_resource_id": str(resource.get("provider_resource_id") or resource_id).strip() or resource_id,
        "display_name": str(resource.get("display_name") or metadata.get("name") or resource_id).strip() or resource_id,
        "metadata": dict(metadata),
    }
    raw_chunking_constraints = resource.get("chunking_constraints")
    if isinstance(raw_chunking_constraints, dict):
        normalized["chunking_constraints"] = dict(raw_chunking_constraints)
    return normalized


def _vectorization_json_payload(
    *,
    supports_named_vectors: bool,
    mode: str,
    embedding_resource: dict[str, Any] | None,
) -> dict[str, Any]:
    default_vector_space: dict[str, Any] = {
        "name": "default",
        "mode": mode,
    }
    if embedding_resource is not None:
        default_vector_space["embedding_resource_id"] = embedding_resource["id"]
    payload = {
        "supports_named_vectors": supports_named_vectors,
        "named_vectors": [],
        "default_vector_space": default_vector_space,
    }
    if embedding_resource is not None:
        payload["embedding_resource"] = embedding_resource
    return payload


def _normalize_options_provider(
    database_url: str,
    provider_row: dict[str, Any],
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    active_binding = platform_repo.get_active_binding_for_provider_instance(
        database_url,
        provider_instance_id=str(provider_row["id"]),
    )
    default_resource_id = None
    if isinstance(active_binding, dict) and isinstance(active_binding.get("default_resource"), dict):
        default_resource_id = _runtime_identifier_for_resource(active_binding["default_resource"]) or None
    if default_resource_id is None and resources:
        default_resource_id = resources[0]["id"]
    is_ready = bool(resources)
    unavailable_reason = None if is_ready else "no_embedding_resources"
    return {
        **_serialize_provider_summary(provider_row),
        "resources": resources,
        "default_resource_id": default_resource_id,
        "is_ready": is_ready,
        "unavailable_reason": unavailable_reason,
    }


def list_vectorization_options(
    database_url: str,
    *,
    config: Any,
    backing_provider_instance_id: str,
) -> dict[str, Any]:
    from . import platform_service

    normalized_provider_id = str(backing_provider_instance_id or "").strip()
    if not normalized_provider_id:
        raise PlatformControlPlaneError(
            "invalid_backing_provider_instance_id",
            "backing_provider_instance_id is required",
            status_code=400,
        )
    provider_row = platform_repo.get_provider_instance(database_url, normalized_provider_id)
    if provider_row is None:
        raise PlatformControlPlaneError(
            "backing_provider_not_found",
            "Backing provider instance was not found",
            status_code=404,
        )
    if str(provider_row.get("capability_key") or "").strip().lower() != CAPABILITY_VECTOR_STORE:
        raise PlatformControlPlaneError(
            "invalid_backing_provider_capability",
            "Backing provider must be a vector store provider",
            status_code=400,
        )
    if not bool(provider_row.get("enabled", True)):
        raise PlatformControlPlaneError(
            "invalid_backing_provider_disabled",
            "Backing provider must be enabled",
            status_code=400,
        )

    embedding_providers: list[dict[str, Any]] = []
    for provider in platform_repo.list_provider_instances(database_url):
        if str(provider.get("capability_key") or "").strip().lower() != CAPABILITY_EMBEDDINGS:
            continue
        if not bool(provider.get("enabled", True)):
            continue
        try:
            adapter = platform_service.resolve_embeddings_adapter(
                database_url,
                config,
                provider_instance_id=str(provider["id"]),
            )
            resources_payload, status_code = adapter.list_resources()
        except PlatformControlPlaneError:
            continue
        if not 200 <= status_code < 300:
            continue
        resources = [
            {
                **normalized,
                **(
                    {
                        "chunking_constraints": serialized_constraints,
                    }
                    if serialized_constraints is not None
                    else {}
                ),
            }
            for item in resources_payload
            if isinstance(item, dict)
            for normalized in [_normalize_embedding_resource(item)]
            if normalized is not None
            for serialized_constraints in [
                serialize_embeddings_chunking_constraints(
                    resolve_embedding_resource_chunking_constraints(
                        database_url,
                        provider_row=provider,
                        resource=normalized,
                    )
                )
            ]
        ]
        embedding_providers.append(_normalize_options_provider(database_url, provider, resources))

    provider_key = str(provider_row.get("provider_key") or "").strip().lower()
    return {
        "backing_provider": _serialize_provider_summary(provider_row),
        "supports_named_vectors": _provider_supports_named_vectors(provider_key),
        "supported_modes": [
            {
                "mode": VECTOR_MODE_VANESSA_EMBEDDINGS,
                "requires_embedding_target": True,
            },
            {
                "mode": VECTOR_MODE_SELF_PROVIDED,
                "requires_embedding_target": False,
            },
        ],
        "embedding_providers": embedding_providers,
    }


def normalize_knowledge_base_vectorization(
    database_url: str,
    *,
    config: Any,
    payload: dict[str, Any],
    is_create: bool,
    existing: dict[str, Any] | None,
    backing_provider: dict[str, Any] | None,
) -> dict[str, Any]:
    if not is_create and any(
        key in payload
        for key in {"vectorization", "vectorization_mode", "embedding_provider_instance_id", "embedding_resource_id"}
    ):
        raise PlatformControlPlaneError(
            "vectorization_immutable",
            "vectorization cannot be changed after creation",
            status_code=400,
        )

    vectorization_payload = payload.get("vectorization")
    if not is_create:
        if isinstance(vectorization_payload, dict):
            raise PlatformControlPlaneError(
                "vectorization_immutable",
                "vectorization cannot be changed after creation",
                status_code=400,
            )
        existing_mode = str(existing.get("vectorization_mode") or "").strip().lower() if existing else ""
        existing_provider = str(existing.get("embedding_provider_instance_id") or "").strip() or None if existing else None
        existing_resource = str(existing.get("embedding_resource_id") or "").strip() or None if existing else None
        existing_json = dict(existing.get("vectorization_json") or {}) if existing else {}
        return {
            "mode": existing_mode or VECTOR_MODE_VANESSA_EMBEDDINGS,
            "embedding_provider_instance_id": existing_provider,
            "embedding_resource_id": existing_resource,
            "vectorization_json": existing_json,
        }

    if not isinstance(vectorization_payload, dict):
        raise PlatformControlPlaneError(
            "invalid_vectorization",
            "vectorization is required",
            status_code=400,
        )
    mode = str(vectorization_payload.get("mode") or "").strip().lower()
    if mode not in SUPPORTED_KB_VECTORIZATION_MODES:
        raise PlatformControlPlaneError(
            "invalid_vectorization_mode",
            "vectorization.mode is unsupported",
            status_code=400,
        )
    backing_provider_key = str((backing_provider or {}).get("provider_key") or "").strip().lower()
    supports_named_vectors = _provider_supports_named_vectors(backing_provider_key)
    if mode == VECTOR_MODE_SELF_PROVIDED:
        if str(vectorization_payload.get("embedding_provider_instance_id") or "").strip() or str(
            vectorization_payload.get("embedding_resource_id") or ""
        ).strip():
            raise PlatformControlPlaneError(
                "invalid_vectorization_target",
                "self_provided vectorization must not include an embeddings target",
                status_code=400,
            )
        return {
            "mode": mode,
            "embedding_provider_instance_id": None,
            "embedding_resource_id": None,
            "vectorization_json": _vectorization_json_payload(
                supports_named_vectors=supports_named_vectors,
                mode=mode,
                embedding_resource=None,
            ),
        }

    embedding_provider_instance_id = str(vectorization_payload.get("embedding_provider_instance_id") or "").strip()
    embedding_resource_id = str(vectorization_payload.get("embedding_resource_id") or "").strip()
    if not embedding_provider_instance_id:
        raise PlatformControlPlaneError(
            "invalid_embedding_provider_instance_id",
            "vectorization.embedding_provider_instance_id is required",
            status_code=400,
        )
    if not embedding_resource_id:
        raise PlatformControlPlaneError(
            "invalid_embedding_resource_id",
            "vectorization.embedding_resource_id is required",
            status_code=400,
        )
    embedding_provider_row = platform_repo.get_provider_instance(database_url, embedding_provider_instance_id)
    if embedding_provider_row is None:
        raise PlatformControlPlaneError(
            "embedding_provider_not_found",
            "Embeddings provider instance was not found",
            status_code=400,
        )
    if str(embedding_provider_row.get("capability_key") or "").strip().lower() != CAPABILITY_EMBEDDINGS:
        raise PlatformControlPlaneError(
            "invalid_embedding_provider_capability",
            "Embeddings target must use an embeddings provider",
            status_code=400,
        )
    if not bool(embedding_provider_row.get("enabled", True)):
        raise PlatformControlPlaneError(
            "invalid_embedding_provider_disabled",
            "Embeddings provider must be enabled",
            status_code=400,
        )

    options = list_vectorization_options(
        database_url,
        config=config,
        backing_provider_instance_id=str((backing_provider or {}).get("id") or ""),
    )
    selected_provider = next(
        (
            item
            for item in options["embedding_providers"]
            if str(item.get("id") or "").strip() == embedding_provider_instance_id
        ),
        None,
    )
    if selected_provider is None:
        raise PlatformControlPlaneError(
            "embedding_provider_unavailable",
            "Selected embeddings provider is not available for KB vectorization",
            status_code=400,
        )
    selected_resource = next(
        (
            item
            for item in selected_provider["resources"]
            if str(item.get("id") or "").strip() == embedding_resource_id
        ),
        None,
    )
    if selected_resource is None:
        raise PlatformControlPlaneError(
            "embedding_resource_not_found",
            "Selected embeddings resource is not available for KB vectorization",
            status_code=400,
        )
    return {
        "mode": mode,
        "embedding_provider_instance_id": embedding_provider_instance_id,
        "embedding_resource_id": embedding_resource_id,
        "vectorization_json": _vectorization_json_payload(
            supports_named_vectors=supports_named_vectors,
            mode=mode,
            embedding_resource=selected_resource,
        ),
    }


def serialize_knowledge_base_vectorization(row: dict[str, Any]) -> dict[str, Any]:
    vectorization_json = dict(row.get("vectorization_json") or {})
    embedding_provider_instance_id = str(row.get("embedding_provider_instance_id") or "").strip() or None
    embedding_resource_id = str(row.get("embedding_resource_id") or "").strip() or None
    raw_resource = vectorization_json.get("embedding_resource")
    embedding_resource = _normalize_embedding_resource(raw_resource) if isinstance(raw_resource, dict) else None
    if embedding_resource is None and embedding_resource_id:
        embedding_resource = {
            "id": embedding_resource_id,
            "provider_resource_id": embedding_resource_id,
            "display_name": embedding_resource_id,
            "metadata": {},
        }
    supports_named_vectors = bool(vectorization_json.get("supports_named_vectors"))
    if not supports_named_vectors:
        supports_named_vectors = _provider_supports_named_vectors(str(row.get("backing_provider_key") or ""))
    return {
        "mode": str(row.get("vectorization_mode") or VECTOR_MODE_VANESSA_EMBEDDINGS).strip().lower(),
        "embedding_provider_instance_id": embedding_provider_instance_id,
        "embedding_resource_id": embedding_resource_id,
        "embedding_provider": (
            {
                "id": embedding_provider_instance_id,
                "slug": str(row.get("embedding_provider_slug") or "").strip() or None,
                "provider_key": str(row.get("embedding_provider_key") or "").strip().lower() or None,
                "display_name": str(row.get("embedding_provider_display_name") or "").strip() or None,
                "enabled": row.get("embedding_provider_enabled")
                if row.get("embedding_provider_enabled") is not None
                else None,
                "capability": str(row.get("embedding_provider_capability") or "").strip().lower() or None,
            }
            if embedding_provider_instance_id
            else None
        ),
        "embedding_resource": embedding_resource,
        "supports_named_vectors": supports_named_vectors,
    }


def require_knowledge_base_text_ingestion_supported(knowledge_base: dict[str, Any]) -> None:
    mode = str(knowledge_base.get("vectorization_mode") or VECTOR_MODE_VANESSA_EMBEDDINGS).strip().lower()
    if mode == VECTOR_MODE_SELF_PROVIDED:
        raise PlatformControlPlaneError(
            "knowledge_base_self_provided_ingestion_unsupported",
            "This knowledge base expects externally supplied vectors, so the current text ingestion flows are unavailable.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base.get("id"), "vectorization_mode": mode},
        )


def require_knowledge_base_query_supported(knowledge_base: dict[str, Any]) -> None:
    mode = str(knowledge_base.get("vectorization_mode") or VECTOR_MODE_VANESSA_EMBEDDINGS).strip().lower()
    if mode == VECTOR_MODE_SELF_PROVIDED:
        raise PlatformControlPlaneError(
            "knowledge_base_self_provided_query_unsupported",
            "This knowledge base expects externally supplied vectors, so text-query retrieval is unavailable.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base.get("id"), "vectorization_mode": mode},
        )


def embed_knowledge_base_texts(
    database_url: str,
    *,
    config: Any,
    knowledge_base: dict[str, Any],
    texts: list[str],
) -> dict[str, Any]:
    from .embeddings_service import embed_text_inputs_with_target

    require_knowledge_base_query_supported(knowledge_base)
    provider_instance_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
    resource_id = str(knowledge_base.get("embedding_resource_id") or "").strip()
    if not provider_instance_id or not resource_id:
        raise PlatformControlPlaneError(
            "knowledge_base_embeddings_not_configured",
            "Knowledge base embeddings target is not configured.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base.get("id")},
        )
    return embed_text_inputs_with_target(
        database_url,
        config,
        texts,
        provider_instance_id=provider_instance_id,
        model=resource_id,
    )


def validate_runtime_vectorization_compatibility(
    knowledge_base: dict[str, Any],
    *,
    active_embeddings_binding: Any,
) -> None:
    require_knowledge_base_query_supported(knowledge_base)
    knowledge_base_provider_instance_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
    active_provider_instance_id = str(getattr(active_embeddings_binding, "provider_instance_id", "") or "").strip()
    if knowledge_base_provider_instance_id != active_provider_instance_id:
        raise PlatformControlPlaneError(
            "knowledge_base_embeddings_provider_mismatch",
            "The active deployment embeddings provider does not match this knowledge base.",
            status_code=409,
            details={
                "knowledge_base_id": knowledge_base.get("id"),
                "knowledge_base_embedding_provider_instance_id": knowledge_base_provider_instance_id or None,
                "active_embedding_provider_instance_id": active_provider_instance_id or None,
                "knowledge_base_embedding_provider_key": str(
                    knowledge_base.get("embedding_provider_key") or ""
                ).strip()
                or None,
                "active_embedding_provider_key": str(getattr(active_embeddings_binding, "provider_key", "") or "").strip()
                or None,
            },
        )
    active_resource_id = _runtime_identifier_for_resource(getattr(active_embeddings_binding, "default_resource", None) or {})
    knowledge_base_resource_id = str(knowledge_base.get("embedding_resource_id") or "").strip()
    if knowledge_base_resource_id != active_resource_id:
        raise PlatformControlPlaneError(
            "knowledge_base_embeddings_resource_mismatch",
            "The active deployment embeddings resource does not match this knowledge base.",
            status_code=409,
            details={
                "knowledge_base_id": knowledge_base.get("id"),
                "knowledge_base_embedding_resource_id": knowledge_base_resource_id or None,
                "active_embedding_resource_id": active_resource_id or None,
            },
        )
