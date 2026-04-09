from __future__ import annotations

import json

from flask import Blueprint, g, jsonify, request

from ...application.context_management_service import (
    ContextManagementRequestError,
    create_context_schema_profile,
    create_context_knowledge_base,
    create_context_knowledge_base_document,
    create_context_knowledge_source,
    delete_context_knowledge_base,
    delete_context_knowledge_base_document,
    delete_context_knowledge_source,
    get_context_knowledge_base_detail,
    list_context_knowledge_base_documents,
    list_context_knowledge_base_sync_runs,
    list_context_knowledge_bases,
    list_context_schema_profiles,
    list_context_source_directories,
    list_context_vectorization_options,
    list_context_knowledge_sources,
    query_context_knowledge_base,
    resync_context_knowledge_base,
    sync_context_knowledge_source,
    update_context_knowledge_base,
    update_context_knowledge_base_document,
    update_context_knowledge_source,
    upload_context_knowledge_base_documents,
)
from ...authz import require_role
from ...config import get_auth_config
from ...services.platform_types import PlatformControlPlaneError

bp = Blueprint("context", __name__)

# Preserve the existing route-module monkeypatch seam while making this
# module the canonical registered HTTP owner.
list_knowledge_bases = list_context_knowledge_bases
list_schema_profiles = list_context_schema_profiles
create_schema_profile = create_context_schema_profile
list_source_directories = list_context_source_directories
list_vectorization_options = list_context_vectorization_options
create_knowledge_base = create_context_knowledge_base
get_knowledge_base_detail = get_context_knowledge_base_detail
update_knowledge_base = update_context_knowledge_base
delete_knowledge_base = delete_context_knowledge_base
resync_knowledge_base = resync_context_knowledge_base
query_knowledge_base = query_context_knowledge_base
list_knowledge_sources = list_context_knowledge_sources
create_knowledge_source = create_context_knowledge_source
update_knowledge_source = update_context_knowledge_source
delete_knowledge_source = delete_context_knowledge_source
sync_knowledge_source = sync_context_knowledge_source
list_knowledge_base_sync_runs = list_context_knowledge_base_sync_runs
list_knowledge_base_documents = list_context_knowledge_base_documents
create_knowledge_base_document = create_context_knowledge_base_document
update_knowledge_base_document = update_context_knowledge_base_document
delete_knowledge_base_document = delete_context_knowledge_base_document
upload_knowledge_base_documents = upload_context_knowledge_base_documents


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


@bp.get("/v1/context/schema-profiles")
@require_role("admin")
def list_schema_profiles_route():
    provider_key = request.args.get("provider_key", "").strip()
    if not provider_key:
        return _json_error(400, "invalid_provider_key", "provider_key is required")
    try:
        schema_profiles = list_schema_profiles(_database_url(), provider_key=provider_key)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"schema_profiles": schema_profiles}), 200


@bp.post("/v1/context/schema-profiles")
@require_role("superadmin")
def create_schema_profile_route():
    try:
        schema_profile = create_schema_profile(
            _database_url(),
            payload=request.get_json(silent=True),
            created_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"schema_profile": schema_profile}), 201


@bp.get("/v1/context/vectorization-options")
@require_role("admin")
def list_vectorization_options_route():
    backing_provider_instance_id = request.args.get("backing_provider_instance_id", "").strip()
    if not backing_provider_instance_id:
        return _json_error(
            400,
            "invalid_backing_provider_instance_id",
            "backing_provider_instance_id is required",
        )
    try:
        options = list_vectorization_options(
            _database_url(),
            config=_config(),
            backing_provider_instance_id=backing_provider_instance_id,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(options), 200


@bp.get("/v1/context/source-directories")
@require_role("admin")
def list_source_directories_route():
    root_id = request.args.get("root_id", "").strip() or None
    relative_path = request.args.get("relative_path", "")
    try:
        payload = list_source_directories(
            _database_url(),
            config=_config(),
            root_id=root_id,
            relative_path=relative_path,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/context/knowledge-bases")
@require_role("admin")
def list_knowledge_bases_route():
    eligible_only = request.args.get("eligible", "").strip().lower() == "true"
    backing_provider_key = request.args.get("backing_provider_key", "").strip() or None
    backing_provider_instance_id = request.args.get("backing_provider_instance_id", "").strip() or None
    try:
        knowledge_bases = list_knowledge_bases(
            _database_url(),
            eligible_only=eligible_only,
            backing_provider_key=backing_provider_key,
            backing_provider_instance_id=backing_provider_instance_id,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_bases": knowledge_bases}), 200


@bp.post("/v1/context/knowledge-bases")
@require_role("superadmin")
def create_knowledge_base_route():
    try:
        knowledge_base = create_knowledge_base(
            _database_url(),
            config=_config(),
            payload=request.get_json(silent=True),
            created_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_base": knowledge_base}), 201


@bp.get("/v1/context/knowledge-bases/<knowledge_base_id>")
@require_role("admin")
def get_knowledge_base_route(knowledge_base_id: str):
    try:
        knowledge_base = get_knowledge_base_detail(_database_url(), knowledge_base_id=knowledge_base_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_base": knowledge_base}), 200


@bp.put("/v1/context/knowledge-bases/<knowledge_base_id>")
@require_role("superadmin")
def update_knowledge_base_route(knowledge_base_id: str):
    try:
        knowledge_base = update_knowledge_base(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=request.get_json(silent=True),
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_base": knowledge_base}), 200


@bp.delete("/v1/context/knowledge-bases/<knowledge_base_id>")
@require_role("superadmin")
def delete_knowledge_base_route(knowledge_base_id: str):
    try:
        delete_knowledge_base(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "knowledge_base_id": knowledge_base_id}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/resync")
@require_role("superadmin")
def resync_knowledge_base_route(knowledge_base_id: str):
    try:
        knowledge_base = resync_knowledge_base(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_base": knowledge_base}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/query")
@require_role("admin")
def query_knowledge_base_route(knowledge_base_id: str):
    try:
        response_payload = query_knowledge_base(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=request.get_json(silent=True),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(response_payload), 200


@bp.get("/v1/context/knowledge-bases/<knowledge_base_id>/sources")
@require_role("admin")
def list_knowledge_sources_route(knowledge_base_id: str):
    try:
        sources = list_knowledge_sources(_database_url(), knowledge_base_id=knowledge_base_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"sources": sources}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/sources")
@require_role("superadmin")
def create_knowledge_source_route(knowledge_base_id: str):
    try:
        source = create_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=request.get_json(silent=True),
            created_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"source": source}), 201


@bp.put("/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>")
@require_role("superadmin")
def update_knowledge_source_route(knowledge_base_id: str, source_id: str):
    try:
        source = update_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            payload=request.get_json(silent=True),
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"source": source}), 200


@bp.delete("/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>")
@require_role("superadmin")
def delete_knowledge_source_route(knowledge_base_id: str, source_id: str):
    try:
        delete_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "source_id": source_id}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>/sync")
@require_role("superadmin")
def sync_knowledge_source_route(knowledge_base_id: str, source_id: str):
    try:
        payload = sync_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/context/knowledge-bases/<knowledge_base_id>/sync-runs")
@require_role("admin")
def list_knowledge_base_sync_runs_route(knowledge_base_id: str):
    try:
        sync_runs = list_knowledge_base_sync_runs(_database_url(), knowledge_base_id=knowledge_base_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"sync_runs": sync_runs}), 200


@bp.get("/v1/context/knowledge-bases/<knowledge_base_id>/documents")
@require_role("admin")
def list_knowledge_base_documents_route(knowledge_base_id: str):
    try:
        documents = list_knowledge_base_documents(_database_url(), knowledge_base_id=knowledge_base_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"documents": documents}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/documents")
@require_role("superadmin")
def create_knowledge_base_document_route(knowledge_base_id: str):
    try:
        document = create_knowledge_base_document(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=request.get_json(silent=True),
            created_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"document": document}), 201


@bp.put("/v1/context/knowledge-bases/<knowledge_base_id>/documents/<document_id>")
@require_role("superadmin")
def update_knowledge_base_document_route(knowledge_base_id: str, document_id: str):
    try:
        document = update_knowledge_base_document(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            payload=request.get_json(silent=True),
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ContextManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"document": document}), 200


@bp.delete("/v1/context/knowledge-bases/<knowledge_base_id>/documents/<document_id>")
@require_role("superadmin")
def delete_knowledge_base_document_route(knowledge_base_id: str, document_id: str):
    try:
        delete_knowledge_base_document(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "document_id": document_id}), 200


@bp.post("/v1/context/knowledge-bases/<knowledge_base_id>/uploads")
@require_role("superadmin")
def upload_knowledge_base_documents_route(knowledge_base_id: str):
    files = request.files.getlist("files")
    raw_metadata = str(request.form.get("metadata") or "").strip()
    metadata = None
    if raw_metadata:
        try:
            parsed_metadata = json.loads(raw_metadata)
        except json.JSONDecodeError:
            return _json_error(400, "invalid_metadata", "metadata must be a JSON object")
        if not isinstance(parsed_metadata, dict):
            return _json_error(400, "invalid_metadata", "metadata must be a JSON object")
        metadata = parsed_metadata
    try:
        payload = upload_knowledge_base_documents(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            files=files,
            metadata=metadata,
            created_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 201
