from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories.model_credentials import (
    create_credential,
    get_active_credential_secret,
    list_credentials_for_user,
    revoke_credential,
)
from ..repositories.model_management import (
    append_audit_event,
    assign_model_to_user,
    register_model,
)
from ..schemas.model_management import CredentialCreateRequest, ModelRegisterRequest, UserModelAssignmentRequest
from ..services.provider_validation import ProviderValidationError, validate_openai_compatible_model
from ..services.model_resolution import list_models_for_user

bp = Blueprint("model_management_v1", __name__)


_ALLOWED_PROVIDERS = {"openai", "anthropic", "hf", "local_filesystem", "openai_compatible"}


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _encryption_key() -> str:
    return get_auth_config().model_credentials_encryption_key


def _serialize_credential(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row.get("id")),
        "owner_user_id": row.get("owner_user_id"),
        "credential_scope": row.get("credential_scope"),
        "provider": row.get("provider_slug"),
        "display_name": row.get("display_name"),
        "api_base_url": row.get("api_base_url"),
        "api_key_last4": row.get("api_key_last4"),
        "is_active": bool(row.get("is_active")),
        "revoked_at": row.get("revoked_at"),
    }


def _serialize_managed_model(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row.get("model_id"),
        "name": row.get("name"),
        "provider": row.get("provider"),
        "provider_model_id": row.get("provider_model_id"),
        "origin": row.get("origin_scope"),
        "backend": row.get("backend_kind"),
        "source": row.get("source_kind"),
        "availability": row.get("availability"),
        "access_scope": row.get("access_scope"),
        "credential_owner": "you" if row.get("origin_scope") == "personal" else "platform",
        "model_size_billion": row.get("model_size_billion"),
        "model_type": row.get("model_type"),
        "comment": row.get("comment"),
        "metadata": row.get("metadata") or {},
    }


@bp.get("/v1/models/credentials")
@require_role("user")
def list_credentials_v1():
    user_id = int(g.current_user["id"])
    role = str(g.current_user.get("role", "user"))
    rows = list_credentials_for_user(_database_url(), requester_user_id=user_id, requester_role=role)
    return jsonify({"credentials": [_serialize_credential(row) for row in rows]}), 200


@bp.post("/v1/models/credentials")
@require_role("user")
def create_credential_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    role = str(g.current_user.get("role", "user"))
    current_user_id = int(g.current_user["id"])

    try:
        request_body = CredentialCreateRequest.from_payload(
            payload,
            current_user_id=current_user_id,
            current_role=role,
            allowed_providers=_ALLOWED_PROVIDERS,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "forbidden_scope":
            return _json_error(403, code, "Only superadmin can create platform credentials")
        if code == "invalid_provider":
            return _json_error(400, code, "Unsupported provider")
        return _json_error(400, code, "Invalid credential payload")

    try:
        created = create_credential(
            _database_url(),
            owner_user_id=request_body.owner_user_id,
            credential_scope=request_body.credential_scope,
            provider_slug=request_body.provider,
            display_name=request_body.display_name,
            api_base_url=request_body.api_base_url,
            api_key=request_body.api_key,
            encryption_key=_encryption_key(),
            created_by_user_id=current_user_id,
        )
    except ValueError as exc:
        return _json_error(400, str(exc), "Invalid credential payload")

    append_audit_event(
        _database_url(),
        actor_user_id=current_user_id,
        event_type="credential.created",
        target_type="credential",
        target_id=str(created["id"]),
        payload={"scope": request_body.credential_scope, "provider": request_body.provider, "owner_user_id": request_body.owner_user_id},
    )

    return jsonify({"credential": _serialize_credential(created)}), 201


@bp.delete("/v1/models/credentials/<credential_id>")
@require_role("user")
def revoke_credential_v1(credential_id: str):
    user_id = int(g.current_user["id"])
    try:
        revoked = revoke_credential(_database_url(), credential_id=credential_id, owner_user_id=user_id)
    except ValueError:
        return _json_error(400, "invalid_credential_id", "credential_id must be a UUID")

    if revoked is None:
        return _json_error(404, "credential_not_found", "Credential not found")

    append_audit_event(
        _database_url(),
        actor_user_id=user_id,
        event_type="credential.revoked",
        target_type="credential",
        target_id=credential_id,
        payload={"owner_user_id": user_id},
    )
    return jsonify({"credential": _serialize_credential(revoked)}), 200


@bp.post("/v1/models/register")
@require_role("user")
def register_model_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    user_id = int(g.current_user["id"])
    role = str(g.current_user.get("role", "user"))

    try:
        request_body = ModelRegisterRequest.from_payload(
            payload,
            current_role=role,
            allowed_providers=_ALLOWED_PROVIDERS,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "forbidden_origin":
            return _json_error(403, code, "Only superadmin can register platform models")
        if code == "invalid_model":
            return _json_error(400, code, "id and name are required")
        if code == "invalid_provider":
            return _json_error(400, code, "Unsupported provider")
        if code == "provider_model_id_required":
            return _json_error(400, code, "provider_model_id is required for external_api models")
        if code == "credential_id_required":
            return _json_error(400, code, "credential_id is required for external_api models")
        return _json_error(400, code, "Invalid model payload")

    if request_body.backend_kind == "external_api":
        credential = get_active_credential_secret(
            _database_url(),
            credential_id=request_body.credential_id or "",
            requester_user_id=user_id,
            requester_role=role,
            encryption_key=_encryption_key(),
        )
        if credential is None:
            return _json_error(404, "credential_not_found", "Active credential not found")

        try:
            validate_openai_compatible_model(
                api_base_url=str(credential.get("api_base_url") or ""),
                api_key=str(credential.get("api_key") or ""),
                model_id=request_body.provider_model_id or "",
            )
        except ProviderValidationError as exc:
            return _json_error(400, str(exc), "Provider validation failed")

    try:
        model = register_model(
            _database_url(),
            model_id=request_body.model_id,
            name=request_body.name,
            provider=request_body.provider,
            provider_model_id=request_body.provider_model_id,
            source_id=request_body.source_id,
            local_path=request_body.local_path,
            origin_scope=request_body.origin_scope,
            backend_kind=request_body.backend_kind,
            source_kind=request_body.source_kind,
            availability=request_body.availability,
            access_scope=request_body.access_scope,
            credential_id=request_body.credential_id,
            model_size_billion=request_body.model_size_billion,
            model_type=request_body.model_type,
            comment=request_body.comment,
            metadata=request_body.metadata,
            registered_by_user_id=user_id,
        )
    except ValueError as exc:
        return _json_error(400, str(exc), "Invalid model payload")

    append_audit_event(
        _database_url(),
        actor_user_id=user_id,
        event_type="model.registered",
        target_type="model",
        target_id=str(model["model_id"]),
        payload={"origin": request_body.origin_scope, "backend": request_body.backend_kind, "provider": request_body.provider},
    )

    return jsonify({"model": _serialize_managed_model(model)}), 201


@bp.post("/v1/models/assignments/user")
@require_role("admin")
def assign_model_user_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        request_body = UserModelAssignmentRequest.from_payload(payload)
    except ValueError:
        return _json_error(400, "invalid_assignment", "model_id and integer user_id are required")

    actor = int(g.current_user["id"])
    assignment = assign_model_to_user(
        _database_url(),
        model_id=request_body.model_id,
        user_id=request_body.user_id,
        actor_user_id=actor,
    )
    append_audit_event(
        _database_url(),
        actor_user_id=actor,
        event_type="model.assignment.user",
        target_type="model",
        target_id=request_body.model_id,
        payload={"user_id": request_body.user_id},
    )
    return jsonify({"assignment": assignment}), 201


@bp.get("/v1/models/available")
@require_role("user")
def list_available_models_v1():
    user_id = int(g.current_user["id"])
    profile, rows = list_models_for_user(_database_url(), user_id=user_id)
    return jsonify({"models": [_serialize_managed_model(row) for row in rows], "runtime_profile": profile}), 200
