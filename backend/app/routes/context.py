from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..services.context_management import (
    create_knowledge_base,
    create_knowledge_base_document,
    create_knowledge_source,
    delete_knowledge_base,
    delete_knowledge_base_document,
    delete_knowledge_source,
    get_knowledge_base_detail,
    list_knowledge_base_documents,
    list_knowledge_base_sync_runs,
    list_knowledge_bases,
    list_knowledge_sources,
    query_knowledge_base,
    resync_knowledge_base,
    sync_knowledge_source,
    update_knowledge_base,
    update_knowledge_base_document,
    update_knowledge_source,
    upload_knowledge_base_documents,
)
from ..services.platform_types import PlatformControlPlaneError

bp = Blueprint("context", __name__)


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


@bp.get("/v1/context/knowledge-bases")
@require_role("admin")
def list_knowledge_bases_route():
    eligible_only = request.args.get("eligible", "").strip().lower() == "true"
    backing_provider_key = request.args.get("backing_provider_key", "").strip() or None
    try:
        knowledge_bases = list_knowledge_bases(
            _database_url(),
            eligible_only=eligible_only,
            backing_provider_key=backing_provider_key,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"knowledge_bases": knowledge_bases}), 200


@bp.post("/v1/context/knowledge-bases")
@require_role("superadmin")
def create_knowledge_base_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        knowledge_base = create_knowledge_base(
            _database_url(),
            config=_config(),
            payload=payload,
            created_by_user_id=int(g.current_user["id"]),
        )
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
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        knowledge_base = update_knowledge_base(
            _database_url(),
            knowledge_base_id=knowledge_base_id,
            payload=payload,
            updated_by_user_id=int(g.current_user["id"]),
        )
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
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        response_payload = query_knowledge_base(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=payload,
        )
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
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        source = create_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=payload,
            created_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"source": source}), 201


@bp.put("/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>")
@require_role("superadmin")
def update_knowledge_source_route(knowledge_base_id: str, source_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        source = update_knowledge_source(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            payload=payload,
            updated_by_user_id=int(g.current_user["id"]),
        )
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
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        document = create_knowledge_base_document(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            payload=payload,
            created_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"document": document}), 201


@bp.put("/v1/context/knowledge-bases/<knowledge_base_id>/documents/<document_id>")
@require_role("superadmin")
def update_knowledge_base_document_route(knowledge_base_id: str, document_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        document = update_knowledge_base_document(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            payload=payload,
            updated_by_user_id=int(g.current_user["id"]),
        )
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
    try:
        payload = upload_knowledge_base_documents(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            files=files,
            created_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 201
