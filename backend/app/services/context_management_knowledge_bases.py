from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from .context_management_serialization import _normalize_knowledge_base_payload, _serialize_knowledge_base
from .context_management_shared import _ensure_knowledge_base_index, _require_knowledge_base
from .platform_types import PlatformControlPlaneError


def list_knowledge_bases(
    database_url: str,
    *,
    eligible_only: bool = False,
    backing_provider_key: str | None = None,
    backing_provider_instance_id: str | None = None,
) -> list[dict[str, Any]]:
    return [_serialize_knowledge_base(row) for row in context_repo.list_knowledge_bases(
        database_url,
        eligible_only=eligible_only,
        backing_provider_key=backing_provider_key,
        backing_provider_instance_id=backing_provider_instance_id,
    )]


def get_knowledge_base_detail(database_url: str, *, knowledge_base_id: str) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    deployment_usage = context_repo.list_knowledge_base_deployment_usage(database_url, knowledge_base_id=knowledge_base_id)
    return {
        **_serialize_knowledge_base(knowledge_base),
        "deployment_usage": [
            {
                "deployment_profile": {
                    "id": str(row.get("deployment_profile_id") or "").strip(),
                    "slug": str(row.get("deployment_profile_slug") or "").strip(),
                    "display_name": str(row.get("deployment_profile_display_name") or "").strip(),
                },
                "capability": str(row.get("capability_key") or "").strip(),
            }
            for row in deployment_usage
        ],
    }


def create_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    normalized = _normalize_knowledge_base_payload(database_url, config, payload, is_create=True)
    knowledge_base = context_repo.create_knowledge_base(
        database_url,
        slug=normalized["slug"],
        display_name=normalized["display_name"],
        description=normalized["description"],
        index_name=normalized["index_name"],
        backing_provider_instance_id=str(normalized["backing_provider_instance_id"]),
        lifecycle_state=normalized["lifecycle_state"],
        sync_status="syncing",
        schema_json=normalized["schema"],
        vectorization_mode=normalized["vectorization"]["mode"],
        embedding_provider_instance_id=normalized["vectorization"]["embedding_provider_instance_id"],
        embedding_resource_id=normalized["vectorization"]["embedding_resource_id"],
        vectorization_json=normalized["vectorization"]["vectorization_json"],
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
    )
    context_repo.mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        updated_by_user_id=created_by_user_id,
        last_sync_summary="Preparing managed knowledge base index.",
    )
    try:
        _ensure_knowledge_base_index(database_url, config, knowledge_base)
    except Exception:
        context_repo.set_knowledge_base_sync_result(
            database_url,
            knowledge_base_id=str(knowledge_base["id"]),
            sync_status="error",
            last_sync_error="Unable to prepare the backing vector index.",
            last_sync_summary="Knowledge base initialization failed.",
            updated_by_user_id=created_by_user_id,
        )
        raise
    refreshed = context_repo.set_knowledge_base_sync_result(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        sync_status="ready",
        last_sync_error=None,
        last_sync_summary="Managed knowledge base index is ready.",
        updated_by_user_id=created_by_user_id,
    )
    return _serialize_knowledge_base(
        context_repo.get_knowledge_base(database_url, str((refreshed or knowledge_base)["id"])) or refreshed or knowledge_base
    )


def update_knowledge_base(
    database_url: str,
    *,
    knowledge_base_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    existing = _require_knowledge_base(database_url, knowledge_base_id)
    normalized = _normalize_knowledge_base_payload(database_url, None, payload, is_create=False, existing=existing)
    if (
        normalized["lifecycle_state"] == "archived"
        and str(existing.get("lifecycle_state") or "").strip().lower() != "archived"
    ):
        binding_count = context_repo.count_deployment_bindings_for_knowledge_base(
            database_url,
            knowledge_base_id=knowledge_base_id,
        )
        if binding_count > 0:
            raise PlatformControlPlaneError(
                "knowledge_base_in_use",
                "Knowledge base is still bound to one or more deployments",
                status_code=409,
                details={"binding_count": binding_count, "knowledge_base_id": knowledge_base_id},
            )
    updated = context_repo.update_knowledge_base(
        database_url,
        knowledge_base_id=knowledge_base_id,
        slug=normalized["slug"],
        display_name=normalized["display_name"],
        description=normalized["description"],
        lifecycle_state=normalized["lifecycle_state"],
        sync_status=str(existing.get("sync_status") or "ready"),
        updated_by_user_id=updated_by_user_id,
    )
    if updated is None:
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)
    return _serialize_knowledge_base(context_repo.get_knowledge_base(database_url, knowledge_base_id) or updated)


def delete_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
) -> None:
    from .context_management_shared import _delete_document_chunks

    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    binding_count = context_repo.count_deployment_bindings_for_knowledge_base(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )
    if binding_count > 0:
        raise PlatformControlPlaneError(
            "knowledge_base_in_use",
            "Knowledge base is still bound to one or more deployments",
            status_code=409,
            details={"binding_count": binding_count, "knowledge_base_id": knowledge_base_id},
        )
    documents = context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)
    for document in documents:
        _delete_document_chunks(
            database_url,
            config,
            knowledge_base=knowledge_base,
            document=document,
        )
    if not context_repo.delete_knowledge_base(database_url, knowledge_base_id):
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)
