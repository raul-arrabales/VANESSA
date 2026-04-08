from __future__ import annotations

from typing import Any

from ..repositories import context_management as context_repo
from .context_management_retrieval_options import normalize_knowledge_base_retrieval_options
from .context_management_retrieval_pipeline import run_knowledge_base_retrieval
from .context_management_retrieval_types import KnowledgeBaseRankedRetrievalResult
from .context_management_serialization import (
    _serialize_query_result,
    _serialize_runtime_knowledge_base,
)
from .context_management_chunking import resolve_knowledge_base_tokenizer
from .context_management_shared import _is_knowledge_base_eligible, _require_knowledge_base
from .context_management_vectorization import (
    require_knowledge_base_query_supported,
)
from .platform_types import CAPABILITY_VECTOR_STORE, PlatformControlPlaneError


def _serialize_ranked_query_results(
    ranked_results: list[KnowledgeBaseRankedRetrievalResult],
    *,
    tokenizer: Any,
) -> list[dict[str, Any]]:
    return [
        _serialize_query_result(
            item,
            chunk_length_tokens=len(tokenizer.encode(item.text.strip())),
        )
        for item in ranked_results
    ]


def query_knowledge_base(
    database_url: str,
    *,
    config: Any,
    knowledge_base_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from .platform_service import resolve_vector_store_adapter

    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    if not _is_knowledge_base_eligible(knowledge_base):
        raise PlatformControlPlaneError(
            "knowledge_base_not_ready",
            "Only active and ready knowledge bases can be queried.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base_id},
        )
    options = normalize_knowledge_base_retrieval_options(payload)
    require_knowledge_base_query_supported(knowledge_base)
    vector_adapter = resolve_vector_store_adapter(database_url, config)
    if str(vector_adapter.binding.provider_instance_id or "").strip() != str(knowledge_base.get("backing_provider_instance_id") or "").strip():
        raise PlatformControlPlaneError(
            "knowledge_base_provider_mismatch",
            "The active deployment vector store provider does not match this knowledge base.",
            status_code=409,
            details={
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_provider_instance_id": knowledge_base.get("backing_provider_instance_id"),
                "active_provider_instance_id": vector_adapter.binding.provider_instance_id,
                "knowledge_base_provider_key": knowledge_base.get("backing_provider_key"),
                "active_provider_key": vector_adapter.binding.provider_key,
            },
        )
    retrieval_execution = run_knowledge_base_retrieval(
        database_url,
        config=config,
        knowledge_base=knowledge_base,
        vector_adapter=vector_adapter,
        options=options,
    )
    tokenizer = resolve_knowledge_base_tokenizer(database_url, knowledge_base=knowledge_base)
    return {
        "knowledge_base_id": str(knowledge_base["id"]),
        "retrieval": {
            "index": retrieval_execution.index,
            "result_count": len(retrieval_execution.results),
            "top_k": options.top_k,
            "search_method": options.search_method,
            "query_preprocessing": options.query_preprocessing,
            **({"hybrid_alpha": options.hybrid_alpha} if options.hybrid_alpha is not None else {}),
        },
        "results": _serialize_ranked_query_results(retrieval_execution.results, tokenizer=tokenizer),
    }


def list_active_runtime_knowledge_bases(
    platform_runtime: dict[str, Any],
    *,
    database_url: str | None = None,
) -> dict[str, Any]:
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    vector_store = capabilities.get(CAPABILITY_VECTOR_STORE) if isinstance(capabilities.get(CAPABILITY_VECTOR_STORE), dict) else {}
    resources = vector_store.get("resources") if isinstance(vector_store.get("resources"), list) else []
    knowledge_bases = [
        _serialize_runtime_knowledge_base(item, default_resource_id=str(vector_store.get("default_resource_id") or "").strip() or None)
        for item in resources
        if isinstance(item, dict) and str(item.get("ref_type") or "").strip().lower() == "knowledge_base"
    ]
    if database_url:
        current_rows = {
            str(row.get("id") or "").strip(): row
            for row in context_repo.get_knowledge_bases(database_url, [str(item["id"]) for item in knowledge_bases])
        }
        knowledge_bases = [
            {
                **item,
                "is_eligible": _is_knowledge_base_eligible(current_rows[item["id"]]),
                "lifecycle_state": str(current_rows[item["id"]].get("lifecycle_state") or "").strip() or None,
                "sync_status": str(current_rows[item["id"]].get("sync_status") or "").strip() or None,
            }
            for item in knowledge_bases
            if item["id"] in current_rows and _is_knowledge_base_eligible(current_rows[item["id"]])
        ]
    default_knowledge_base_id = next((item["id"] for item in knowledge_bases if item["is_default"]), None)
    if default_knowledge_base_id is None and len(knowledge_bases) == 1:
        default_knowledge_base_id = knowledge_bases[0]["id"]
    selection_mode = str((vector_store.get("resource_policy") or {}).get("selection_mode") or "explicit").strip().lower()
    configuration_message = None
    if not knowledge_bases:
        if selection_mode == "dynamic_namespace":
            configuration_message = (
                "The active deployment uses dynamic vector namespaces and has no managed knowledge bases bound."
            )
        else:
            configuration_message = "The active deployment has no managed knowledge bases bound."
    return {
        "knowledge_bases": knowledge_bases,
        "default_knowledge_base_id": default_knowledge_base_id,
        "selection_required": len(knowledge_bases) > 1 and default_knowledge_base_id is None,
        "configuration_message": configuration_message,
    }


def resolve_runtime_knowledge_base_selection(
    platform_runtime: dict[str, Any],
    *,
    database_url: str | None = None,
    knowledge_base_id: str | None,
) -> dict[str, Any]:
    options = list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url)
    knowledge_bases = options["knowledge_bases"]
    normalized_id = str(knowledge_base_id or "").strip() or None
    if not knowledge_bases:
        raise PlatformControlPlaneError(
            "knowledge_base_not_configured",
            str(options.get("configuration_message") or "No managed knowledge bases are bound to the active deployment."),
            status_code=409,
        )
    if normalized_id:
        selected = next((item for item in knowledge_bases if item["id"] == normalized_id), None)
        if selected is None:
            raise PlatformControlPlaneError(
                "knowledge_base_not_bound",
                "Requested knowledge base is not bound to the active deployment",
                status_code=403,
                details={"knowledge_base_id": normalized_id},
            )
        return selected
    if options["default_knowledge_base_id"]:
        selected = next((item for item in knowledge_bases if item["id"] == options["default_knowledge_base_id"]), None)
        if selected is not None:
            return selected
    if len(knowledge_bases) == 1:
        return knowledge_bases[0]
    raise PlatformControlPlaneError(
        "knowledge_base_required",
        "Select a knowledge base before starting knowledge chat.",
        status_code=400,
    )
