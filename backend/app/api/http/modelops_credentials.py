from __future__ import annotations

from flask import g, jsonify, request

from ...application.modelops_credentials_service import build_create_credential_request
from ...authz import require_role
from ...services.modelops_common import ModelOpsError


def register_modelops_credentials_routes(
    bp,
    *,
    config_getter,
    json_error_fn,
    serialize_credential_fn,
    create_credential_fn,
    list_credentials_for_user_fn,
    revoke_credential_fn,
    append_audit_event_fn,
):
    @bp.get("/v1/modelops/credentials")
    @require_role("user")
    def list_modelops_credentials_route():
        rows = list_credentials_for_user_fn(
            config_getter().database_url,
            requester_user_id=int(g.current_user["id"]),
            requester_role=str(g.current_user.get("role", "user")),
        )
        return jsonify({"credentials": [serialize_credential_fn(row) for row in rows]}), 200

    @bp.post("/v1/modelops/credentials")
    @require_role("user")
    def create_modelops_credentials_route():
        current_user_id = int(g.current_user["id"])
        role = str(g.current_user.get("role", "user"))
        try:
            credential_request = build_create_credential_request(
                request.get_json(silent=True),
                current_user_id=current_user_id,
                actor_role=role,
            )
            created = create_credential_fn(
                config_getter().database_url,
                **credential_request,
                encryption_key=config_getter().model_credentials_encryption_key,
                created_by_user_id=current_user_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=current_user_id,
            event_type="credential.created",
            target_type="credential",
            target_id=str(created["id"]),
            payload={
                "owner_user_id": credential_request["owner_user_id"],
                "credential_scope": credential_request["credential_scope"],
            },
        )
        return jsonify({"credential": serialize_credential_fn(created)}), 201

    @bp.delete("/v1/modelops/credentials/<credential_id>")
    @require_role("user")
    def delete_modelops_credential_route(credential_id: str):
        try:
            revoke_result = revoke_credential_fn(
                config_getter().database_url,
                credential_id=credential_id,
                owner_user_id=int(g.current_user["id"]),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        if revoke_result is None:
            return json_error_fn(404, "credential_not_found", "Credential not found")
        if isinstance(revoke_result, dict) and isinstance(revoke_result.get("credential"), dict):
            revoked = revoke_result["credential"]
            affected_models = [
                str(item.get("model_id"))
                for item in (revoke_result.get("affected_models") or [])
                if isinstance(item, dict) and item.get("model_id")
            ]
        else:
            revoked = revoke_result
            affected_models = []

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="credential.revoked",
            target_type="credential",
            target_id=credential_id,
            payload={"affected_model_count": len(affected_models)},
        )
        return jsonify({
            "credential": serialize_credential_fn(revoked),
            "affected_models": affected_models,
            "affected_model_count": len(affected_models),
        }), 200
