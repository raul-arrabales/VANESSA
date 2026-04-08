from __future__ import annotations

"""Public context-management service facade for cross-domain callers."""

from .context_management_documents import (
    create_knowledge_base_document,
    delete_knowledge_base_document,
    list_knowledge_base_documents,
    resync_knowledge_base,
    update_knowledge_base_document,
    upload_knowledge_base_documents,
)
from .context_management_knowledge_bases import (
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base_detail,
    list_knowledge_bases,
    update_knowledge_base,
)
from .context_management_runtime import (
    list_active_runtime_knowledge_bases,
    query_knowledge_base,
    resolve_runtime_knowledge_base_selection,
)
from .context_management_schema_profiles import create_schema_profile, list_schema_profiles
from .context_management_serialization import build_knowledge_base_binding_resource
from .context_management_sources import (
    create_knowledge_source,
    delete_knowledge_source,
    list_knowledge_base_sync_runs,
    list_knowledge_sources,
    list_source_directories,
    sync_knowledge_source,
    update_knowledge_source,
)
from .context_management_vectorization import list_vectorization_options

__all__ = [
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
]
