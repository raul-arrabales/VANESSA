from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from .context_management_ingestion import (
    _iter_source_files,
    _parse_source_documents,
    _source_document_changed,
    _source_document_id,
    _source_document_key,
)
from .context_management_serialization import _normalize_knowledge_source_payload, _serialize_knowledge_base, _serialize_knowledge_source, _serialize_sync_run
from .context_management_shared import (
    _chunk_knowledge_base_text,
    _configured_source_roots,
    _delete_document_chunks,
    _mark_knowledge_base_sync_error,
    _mark_knowledge_base_sync_ready,
    _mark_knowledge_base_syncing,
    _normalize_source_relative_path,
    normalize_knowledge_source_sync_failure,
    _refresh_document_count,
    _require_knowledge_base,
    _require_knowledge_source,
    _resolve_source_directory,
    _upsert_document_chunks,
)
from .context_management_types import SourceSyncSummary
from .context_management_vectorization import require_knowledge_base_text_ingestion_supported
from .platform_types import PlatformControlPlaneError


def _resolve_source_browser_root(
    config: AuthConfig,
    *,
    root_id: str | None,
    relative_path: str,
) -> dict[str, Any]:
    roots = _configured_source_roots(config)
    if root_id:
        for root in roots:
            if str(root["id"]) == root_id:
                return root
        raise PlatformControlPlaneError("invalid_source_root", "Selected source root was not found.", status_code=400)
    if relative_path:
        matching_roots: list[dict[str, Any]] = []
        for root in roots:
            root_path = Path(root["path"])
            candidate = (root_path / relative_path).resolve()
            try:
                candidate.relative_to(root_path)
            except ValueError:
                continue
            if candidate.exists() and candidate.is_dir():
                matching_roots.append(root)
        if len(matching_roots) == 1:
            return matching_roots[0]
    return roots[0]


def list_source_directories(
    *,
    config: AuthConfig,
    root_id: str | None = None,
    relative_path: str | None = None,
) -> dict[str, Any]:
    normalized_relative_path = _normalize_source_relative_path(relative_path or "")
    roots = _configured_source_roots(config)
    selected_root = _resolve_source_browser_root(
        config,
        root_id=root_id,
        relative_path=normalized_relative_path,
    )
    root_path = Path(selected_root["path"])
    current_directory = root_path
    if normalized_relative_path:
        current_directory = (root_path / normalized_relative_path).resolve()
        try:
            current_directory.relative_to(root_path)
        except ValueError as exc:
            raise PlatformControlPlaneError(
                "invalid_source_relative_path",
                "relative_path must stay within an allowlisted context source root.",
                status_code=400,
            ) from exc
        if not current_directory.exists():
            raise PlatformControlPlaneError(
                "knowledge_source_path_not_found",
                "Knowledge source directory was not found under the configured source roots.",
                status_code=400,
                details={"relative_path": normalized_relative_path},
            )
        if not current_directory.is_dir():
            raise PlatformControlPlaneError(
                "knowledge_source_not_directory",
                "Knowledge source path must point to a directory.",
                status_code=400,
                details={"relative_path": normalized_relative_path},
            )
    directories = []
    if current_directory.exists() and current_directory.is_dir():
        directories = [
            {
                "name": child.name,
                "relative_path": child.relative_to(root_path).as_posix(),
            }
            for child in sorted(current_directory.iterdir(), key=lambda item: item.name.lower())
            if child.is_dir()
        ]
    parent_relative_path: str | None = None
    if normalized_relative_path:
        parent = current_directory.parent
        if parent != current_directory:
            try:
                parent_relative = parent.relative_to(root_path).as_posix()
            except ValueError:
                parent_relative = ""
            parent_relative_path = "" if parent_relative == "." else parent_relative
    return {
        "roots": [{"id": str(root["id"]), "display_name": str(root["display_name"])} for root in roots],
        "selected_root_id": str(selected_root["id"]),
        "current_relative_path": normalized_relative_path,
        "directories": directories,
        "parent_relative_path": parent_relative_path,
    }


def list_knowledge_sources(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    _require_knowledge_base(database_url, knowledge_base_id)
    return [_serialize_knowledge_source(row) for row in context_repo.list_knowledge_sources(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )]


def create_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    normalized = _normalize_knowledge_source_payload(
        payload,
        knowledge_base_schema=dict(knowledge_base.get("schema_json") or {}),
    )
    _resolve_source_directory(config, normalized["relative_path"], require_exists=True)
    source = context_repo.create_knowledge_source(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_type=normalized["source_type"],
        display_name=normalized["display_name"],
        relative_path=normalized["relative_path"],
        include_globs=normalized["include_globs"],
        exclude_globs=normalized["exclude_globs"],
        metadata_json=normalized["metadata"],
        lifecycle_state=normalized["lifecycle_state"],
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
    )
    return _serialize_knowledge_source(source)


def update_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    existing = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    normalized = _normalize_knowledge_source_payload(
        payload,
        knowledge_base_schema=dict(knowledge_base.get("schema_json") or {}),
        existing=existing,
    )
    _resolve_source_directory(config, normalized["relative_path"], require_exists=True)
    updated = context_repo.update_knowledge_source(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        display_name=normalized["display_name"],
        relative_path=normalized["relative_path"],
        include_globs=normalized["include_globs"],
        exclude_globs=normalized["exclude_globs"],
        metadata_json=normalized["metadata"],
        lifecycle_state=normalized["lifecycle_state"],
        updated_by_user_id=updated_by_user_id,
    )
    if updated is None:
        raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
    return _serialize_knowledge_source(updated)


def delete_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int | None,
) -> None:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    source = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    source_documents = context_repo.list_source_documents(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
    )
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary=f"Removing managed source '{source['display_name']}' and its indexed documents.",
    )
    try:
        for document in source_documents:
            _delete_document_chunks(
                database_url,
                config,
                knowledge_base=knowledge_base,
                document=document,
            )
            context_repo.delete_document(
                database_url,
                knowledge_base_id=knowledge_base_id,
                document_id=str(document["id"]),
            )
        if not context_repo.delete_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id):
            raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Removed managed source '{source['display_name']}' and {len(source_documents)} sourced document(s).",
        )
    except Exception:
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Removing managed source '{source['display_name']}' failed.",
        )
        raise


def list_knowledge_base_sync_runs(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    _require_knowledge_base(database_url, knowledge_base_id)
    return [_serialize_sync_run(row) for row in context_repo.list_sync_runs(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )]


def sync_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    source = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    if str(source.get("lifecycle_state") or "").strip().lower() != "active":
        raise PlatformControlPlaneError(
            "knowledge_source_inactive",
            "Only active knowledge sources can be synced.",
            status_code=409,
            details={"source_id": source_id, "lifecycle_state": source.get("lifecycle_state")},
        )
    _, source_directory = _resolve_source_directory(config, str(source.get("relative_path") or "").strip(), require_exists=True)
    run = context_repo.create_sync_run(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        created_by_user_id=updated_by_user_id,
    )
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary=f"Syncing managed source '{source['display_name']}'.",
    )
    context_repo.mark_knowledge_source_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
    )
    try:
        result = _sync_knowledge_source_documents(
            database_url,
            config,
            knowledge_base=knowledge_base,
            source=source,
            source_directory=source_directory,
            updated_by_user_id=updated_by_user_id,
        )
        finished_run = context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="ready",
            scanned_file_count=result["scanned_file_count"],
            changed_file_count=result["changed_file_count"],
            deleted_file_count=result["deleted_file_count"],
            created_document_count=result["created_document_count"],
            updated_document_count=result["updated_document_count"],
            deleted_document_count=result["deleted_document_count"],
            error_summary=None,
        )
        refreshed_source = context_repo.set_knowledge_source_sync_result(
            database_url,
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            last_sync_status="ready",
            last_sync_error=None,
        )
        refreshed_kb = _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=(
                f"Source '{source['display_name']}' synced "
                f"{result['created_document_count']} created, "
                f"{result['updated_document_count']} updated, "
                f"{result['deleted_document_count']} deleted document(s)."
            ),
        )
        return {
            "knowledge_base": _serialize_knowledge_base(
                context_repo.get_knowledge_base(database_url, knowledge_base_id) or refreshed_kb or knowledge_base
            ),
            "source": _serialize_knowledge_source(refreshed_source or source),
            "sync_run": _serialize_sync_run(finished_run or run),
        }
    except Exception as exc:
        normalized_failure = normalize_knowledge_source_sync_failure(
            exc,
            source_id=source_id,
            source_display_name=str(source.get("display_name") or "").strip(),
            knowledge_base_id=knowledge_base_id,
            sync_run_id=str(run.get("id") or "").strip(),
        )
        finished_run = context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="error",
            scanned_file_count=0,
            changed_file_count=0,
            deleted_file_count=0,
            created_document_count=0,
            updated_document_count=0,
            deleted_document_count=0,
            error_summary=normalized_failure.message,
        )
        refreshed_source = context_repo.set_knowledge_source_sync_result(
            database_url,
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            last_sync_status="error",
            last_sync_error=normalized_failure.message,
        )
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Source '{source['display_name']}' sync failed.",
        )
        raise PlatformControlPlaneError(
            normalized_failure.error.code,
            normalized_failure.message,
            status_code=normalized_failure.error.status_code,
            details={
                **(normalized_failure.error.details if isinstance(normalized_failure.error.details, dict) else {}),
                "sync_run_id": str((finished_run or run).get("id") or "").strip(),
                "last_sync_status": str((refreshed_source or source).get("last_sync_status") or "").strip() or "error",
            },
        ) from exc


def _sync_knowledge_source_documents(
    database_url: str,
    config: AuthConfig,
    *,
    knowledge_base: dict[str, Any],
    source: dict[str, Any],
    source_directory: Path,
    updated_by_user_id: int | None,
) -> SourceSyncSummary:
    scanned_file_count = 0
    created_document_count = 0
    updated_document_count = 0
    deleted_document_count = 0
    changed_paths: set[str] = set()
    deleted_paths: set[str] = set()
    seen_keys: set[str] = set()
    source_id = str(source["id"])
    include_globs = list(source.get("include_globs") or [])
    exclude_globs = list(source.get("exclude_globs") or [])

    for file_path, relative_path in _iter_source_files(
        source_directory,
        include_globs=include_globs,
        exclude_globs=exclude_globs,
    ):
        scanned_file_count += 1
        parsed_documents = _parse_source_documents(file_path, relative_path=relative_path, source=source)
        for position, parsed_document in enumerate(parsed_documents):
            source_document_key = _source_document_key(relative_path, position)
            seen_keys.add(source_document_key)
            existing = context_repo.get_document_by_source_key(
                database_url,
                knowledge_base_id=str(knowledge_base["id"]),
                source_id=source_id,
                source_document_key=source_document_key,
            )
            chunks = _chunk_knowledge_base_text(
                database_url,
                knowledge_base=knowledge_base,
                text=parsed_document["text"],
            )
            if existing is None:
                document = context_repo.create_document(
                    database_url,
                    document_id=_source_document_id(source_id, source_document_key),
                    knowledge_base_id=str(knowledge_base["id"]),
                    title=parsed_document["title"],
                    source_type=parsed_document["source_type"],
                    source_name=parsed_document["source_name"],
                    uri=parsed_document["uri"],
                    text=parsed_document["text"],
                    metadata_json=parsed_document["metadata"],
                    chunk_count=len(chunks),
                    source_id=source_id,
                    source_path=relative_path,
                    source_document_key=source_document_key,
                    managed_by_source=True,
                    created_by_user_id=updated_by_user_id,
                    updated_by_user_id=updated_by_user_id,
                )
                _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document, chunks=chunks)
                created_document_count += 1
                changed_paths.add(relative_path)
                continue
            if not _source_document_changed(
                existing,
                parsed_document=parsed_document,
                chunk_count=len(chunks),
                source_path=relative_path,
                source_document_key=source_document_key,
            ):
                continue
            _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=existing)
            updated = context_repo.update_document(
                database_url,
                knowledge_base_id=str(knowledge_base["id"]),
                document_id=str(existing["id"]),
                title=parsed_document["title"],
                source_type=parsed_document["source_type"],
                source_name=parsed_document["source_name"],
                uri=parsed_document["uri"],
                text=parsed_document["text"],
                metadata_json=parsed_document["metadata"],
                chunk_count=len(chunks),
                source_id=source_id,
                source_path=relative_path,
                source_document_key=source_document_key,
                managed_by_source=True,
                updated_by_user_id=updated_by_user_id,
            )
            if updated is None:
                raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
            _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=updated, chunks=chunks)
            updated_document_count += 1
            changed_paths.add(relative_path)

    existing_documents = context_repo.list_source_documents(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        source_id=source_id,
    )
    for document in existing_documents:
        source_document_key = str(document.get("source_document_key") or "").strip()
        if source_document_key in seen_keys:
            continue
        _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document)
        context_repo.delete_document(
            database_url,
            knowledge_base_id=str(knowledge_base["id"]),
            document_id=str(document["id"]),
        )
        deleted_document_count += 1
        source_path = str(document.get("source_path") or "").strip()
        if source_path:
            deleted_paths.add(source_path)

    _refresh_document_count(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        updated_by_user_id=updated_by_user_id,
    )
    return {
        "scanned_file_count": scanned_file_count,
        "changed_file_count": len(changed_paths),
        "deleted_file_count": len(deleted_paths),
        "created_document_count": created_document_count,
        "updated_document_count": updated_document_count,
        "deleted_document_count": deleted_document_count,
    }
