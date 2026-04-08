from __future__ import annotations

from app.services import context_management


def test_context_management_facade_exports_only_public_entrypoints() -> None:
    expected_public_surface = {
        "build_knowledge_base_binding_resource",
        "create_knowledge_base",
        "create_knowledge_base_document",
        "create_knowledge_source",
        "create_schema_profile",
        "delete_knowledge_base",
        "delete_knowledge_base_document",
        "delete_knowledge_source",
        "get_knowledge_base_detail",
        "list_active_runtime_knowledge_bases",
        "list_knowledge_base_documents",
        "list_knowledge_base_sync_runs",
        "list_knowledge_bases",
        "list_knowledge_sources",
        "list_schema_profiles",
        "list_source_directories",
        "list_vectorization_options",
        "query_knowledge_base",
        "resolve_runtime_knowledge_base_selection",
        "resync_knowledge_base",
        "sync_knowledge_source",
        "update_knowledge_base",
        "update_knowledge_base_document",
        "update_knowledge_source",
        "upload_knowledge_base_documents",
    }

    assert set(context_management.__all__) == expected_public_surface
    assert not hasattr(context_management, "context_repo")
    assert not hasattr(context_management, "normalize_knowledge_base_retrieval_options")
    assert not hasattr(context_management, "_chunk_document_id")
    assert not hasattr(context_management, "_serialize_knowledge_base")
