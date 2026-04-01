from __future__ import annotations

from typing import Any, TypedDict, TypeAlias

KnowledgeBaseRecord: TypeAlias = dict[str, Any]
KnowledgeSchemaProfileRecord: TypeAlias = dict[str, Any]
KnowledgeDocumentRecord: TypeAlias = dict[str, Any]
KnowledgeSourceRecord: TypeAlias = dict[str, Any]
KnowledgeSyncRunRecord: TypeAlias = dict[str, Any]
KnowledgeBaseDetailPayload: TypeAlias = dict[str, Any]
RuntimeKnowledgeBaseOption: TypeAlias = dict[str, Any]


class ParsedIngestionDocument(TypedDict):
    title: str
    source_type: str
    source_name: str | None
    uri: str | None
    text: str
    metadata: dict[str, Any]


class SourceSyncSummary(TypedDict):
    scanned_file_count: int
    changed_file_count: int
    deleted_file_count: int
    created_document_count: int
    updated_document_count: int
    deleted_document_count: int


_SUPPORTED_SCHEMA_PROPERTY_TYPES = {"text", "number", "int", "boolean"}
_SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".md", ".json", ".jsonl", ".pdf"}
_KB_LIFECYCLE_STATES = {"active", "archived"}
_KB_SYNC_STATES = {"ready", "syncing", "error"}
_KB_VECTORIZATION_MODES = {"vanessa_embeddings", "self_provided"}
_SOURCE_TYPES = {"local_directory"}
_SOURCE_LIFECYCLE_STATES = {"active", "archived"}
_SOURCE_SYNC_STATES = {"idle", "syncing", "ready", "error"}
_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE = 650
_MAX_FILE_SIZE_BYTES = 1_000_000
_MAX_UPLOAD_FILES = 10
_MAX_UPLOAD_DOCUMENTS = 100
