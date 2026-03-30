from __future__ import annotations

from typing import Any

from ..services.context_management import (
    create_knowledge_base as _create_knowledge_base,
    create_knowledge_base_document as _create_knowledge_base_document,
    create_schema_profile as _create_schema_profile,
    create_knowledge_source as _create_knowledge_source,
    delete_knowledge_base as _delete_knowledge_base,
    delete_knowledge_base_document as _delete_knowledge_base_document,
    delete_knowledge_source as _delete_knowledge_source,
    get_knowledge_base_detail as _get_knowledge_base_detail,
    list_knowledge_base_documents as _list_knowledge_base_documents,
    list_knowledge_base_sync_runs as _list_knowledge_base_sync_runs,
    list_knowledge_bases as _list_knowledge_bases,
    list_schema_profiles as _list_schema_profiles,
    list_knowledge_sources as _list_knowledge_sources,
    query_knowledge_base as _query_knowledge_base,
    resync_knowledge_base as _resync_knowledge_base,
    sync_knowledge_source as _sync_knowledge_source,
    update_knowledge_base as _update_knowledge_base,
    update_knowledge_base_document as _update_knowledge_base_document,
    update_knowledge_source as _update_knowledge_source,
    upload_knowledge_base_documents as _upload_knowledge_base_documents,
)


class ContextManagementRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContextManagementRequestError(status_code=400, code="invalid_payload", message="Expected JSON object")
    return payload


def list_context_knowledge_bases(
    database_url: str,
    *,
    eligible_only: bool,
    backing_provider_key: str | None,
    backing_provider_instance_id: str | None,
):
    return _list_knowledge_bases(
        database_url,
        eligible_only=eligible_only,
        backing_provider_key=backing_provider_key,
        backing_provider_instance_id=backing_provider_instance_id,
    )


def list_context_schema_profiles(database_url: str, *, provider_key: str):
    return _list_schema_profiles(database_url, provider_key=provider_key)


def create_context_schema_profile(database_url: str, *, payload: Any, created_by_user_id: int):
    return _create_schema_profile(
        database_url,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def create_context_knowledge_base(database_url: str, *, config, payload: Any, created_by_user_id: int):
    return _create_knowledge_base(
        database_url,
        config=config,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def get_context_knowledge_base_detail(database_url: str, *, knowledge_base_id: str):
    return _get_knowledge_base_detail(database_url, knowledge_base_id=knowledge_base_id)


def update_context_knowledge_base(
    database_url: str,
    *,
    knowledge_base_id: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _update_knowledge_base(
        database_url,
        knowledge_base_id=knowledge_base_id,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def delete_context_knowledge_base(database_url: str, *, config, knowledge_base_id: str) -> None:
    _delete_knowledge_base(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
    )


def resync_context_knowledge_base(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    updated_by_user_id: int,
):
    return _resync_knowledge_base(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
    )


def query_context_knowledge_base(database_url: str, *, config, knowledge_base_id: str, payload: Any):
    return _query_knowledge_base(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        payload=_require_json_object(payload),
    )


def list_context_knowledge_sources(database_url: str, *, knowledge_base_id: str):
    return _list_knowledge_sources(database_url, knowledge_base_id=knowledge_base_id)


def create_context_knowledge_source(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    payload: Any,
    created_by_user_id: int,
):
    return _create_knowledge_source(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def update_context_knowledge_source(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    source_id: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _update_knowledge_source(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def delete_context_knowledge_source(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int,
) -> None:
    _delete_knowledge_source(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        updated_by_user_id=updated_by_user_id,
    )


def sync_context_knowledge_source(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int,
):
    return _sync_knowledge_source(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        updated_by_user_id=updated_by_user_id,
    )


def list_context_knowledge_base_sync_runs(database_url: str, *, knowledge_base_id: str):
    return _list_knowledge_base_sync_runs(database_url, knowledge_base_id=knowledge_base_id)


def list_context_knowledge_base_documents(database_url: str, *, knowledge_base_id: str):
    return _list_knowledge_base_documents(database_url, knowledge_base_id=knowledge_base_id)


def create_context_knowledge_base_document(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    payload: Any,
    created_by_user_id: int,
):
    return _create_knowledge_base_document(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def update_context_knowledge_base_document(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    document_id: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _update_knowledge_base_document(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def delete_context_knowledge_base_document(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    document_id: str,
    updated_by_user_id: int,
) -> None:
    _delete_knowledge_base_document(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        updated_by_user_id=updated_by_user_id,
    )


def upload_context_knowledge_base_documents(
    database_url: str,
    *,
    config,
    knowledge_base_id: str,
    files,
    created_by_user_id: int,
):
    return _upload_knowledge_base_documents(
        database_url,
        config=config,
        knowledge_base_id=knowledge_base_id,
        files=files,
        created_by_user_id=created_by_user_id,
    )
