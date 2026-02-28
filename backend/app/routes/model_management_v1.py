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
    list_models_visible_to_user,
    register_model,
)
from ..services.provider_validation import ProviderValidationError, validate_openai_compatible_model
from ..services.runtime_profile_service import resolve_runtime_profile

bp = Blueprint("model_management_v1", __name__)


_ALLOWED_PROVIDERS = {"openai", "anthropic", "hf", "local_filesystem", "openai_compatible"}


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _encryption_key() -> str:
    return get_auth_config().jwt_secret


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
    requested_scope = str(payload.get("credential_scope", "personal")).strip().lower() or "personal"

    if requested_scope == "platform" and role != "superadmin":
        return _json_error(403, "forbidden_scope", "Only superadmin can create platform credentials")

    owner_user_id = int(payload.get("owner_user_id", current_user_id))
    if requested_scope == "personal":
        owner_user_id = current_user_id

    provider = str(payload.get("provider", "openai_compatible")).strip().lower()
    if provider not in _ALLOWED_PROVIDERS:
        return _json_error(400, "invalid_provider", "Unsupported provider")

    api_key = str(payload.get("api_key", ""))
    display_name = str(payload.get("display_name", "")).strip() or f"{provider}-key"

    try:
        created = create_credential(
            _database_url(),
            owner_user_id=owner_user_id,
            credential_scope=requested_scope,
            provider_slug=provider,
            display_name=display_name,
            api_base_url=str(payload.get("api_base_url", "")).strip() or None,
            api_key=api_key,
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
        payload={"scope": requested_scope, "provider": provider, "owner_user_id": owner_user_id},
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

    model_id = str(payload.get("id", "")).strip()
    name = str(payload.get("name", "")).strip()
    provider = str(payload.get("provider", "openai_compatible")).strip().lower()
    backend_kind = str(payload.get("backend", "external_api")).strip().lower()
    origin_scope = str(payload.get("origin", "personal")).strip().lower()

    if not model_id or not name:
        return _json_error(400, "invalid_model", "id and name are required")
    if provider not in _ALLOWED_PROVIDERS:
        return _json_error(400, "invalid_provider", "Unsupported provider")
    if origin_scope == "platform" and role != "superadmin":
        return _json_error(403, "forbidden_origin", "Only superadmin can register platform models")

    source_kind = str(payload.get("source", "external_provider" if backend_kind == "external_api" else "local_folder")).strip().lower()
    availability = str(payload.get("availability", "online_only" if backend_kind == "external_api" else "offline_ready")).strip().lower()
    access_scope = str(payload.get("access_scope", "private" if origin_scope == "personal" else "assigned")).strip().lower()
    provider_model_id = str(payload.get("provider_model_id", "")).strip() or None
    credential_id = str(payload.get("credential_id", "")).strip() or None

    if backend_kind == "external_api":
        if not provider_model_id:
            return _json_error(400, "provider_model_id_required", "provider_model_id is required for external_api models")
        if not credential_id:
            return _json_error(400, "credential_id_required", "credential_id is required for external_api models")
        credential = get_active_credential_secret(
            _database_url(),
            credential_id=credential_id,
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
                model_id=provider_model_id,
            )
        except ProviderValidationError as exc:
            return _json_error(400, str(exc), "Provider validation failed")

    try:
        model = register_model(
            _database_url(),
            model_id=model_id,
            name=name,
            provider=provider,
            provider_model_id=provider_model_id,
            source_id=str(payload.get("source_id", "")).strip() or None,
            local_path=str(payload.get("local_path", "")).strip() or None,
            origin_scope=origin_scope,
            backend_kind=backend_kind,
            source_kind=source_kind,
            availability=availability,
            access_scope=access_scope,
            credential_id=credential_id,
            model_size_billion=float(payload.get("model_size_billion")) if payload.get("model_size_billion") is not None else None,
            model_type=str(payload.get("model_type", "")).strip() or None,
            comment=str(payload.get("comment", "")).strip() or None,
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
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
        payload={"origin": origin_scope, "backend": backend_kind, "provider": provider},
    )

    return jsonify({"model": _serialize_managed_model(model)}), 201


@bp.post("/v1/models/assignments/user")
@require_role("admin")
def assign_model_user_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    user_id_raw = payload.get("user_id")
    if not model_id or not isinstance(user_id_raw, int):
        return _json_error(400, "invalid_assignment", "model_id and integer user_id are required")

    actor = int(g.current_user["id"])
    assignment = assign_model_to_user(_database_url(), model_id=model_id, user_id=user_id_raw, actor_user_id=actor)
    append_audit_event(
        _database_url(),
        actor_user_id=actor,
        event_type="model.assignment.user",
        target_type="model",
        target_id=model_id,
        payload={"user_id": user_id_raw},
    )
    return jsonify({"assignment": assignment}), 201


@bp.get("/v1/models/available")
@require_role("user")
def list_available_models_v1():
    user_id = int(g.current_user["id"])
    profile = resolve_runtime_profile(_database_url())
    rows = list_models_visible_to_user(_database_url(), user_id=user_id, runtime_profile=profile)
    return jsonify({"models": [_serialize_managed_model(row) for row in rows], "runtime_profile": profile}), 200
