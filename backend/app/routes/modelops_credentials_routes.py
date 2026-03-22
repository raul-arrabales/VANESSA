from __future__ import annotations

from flask import g, jsonify, request

from ..authz import require_role


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
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return json_error_fn(400, "invalid_payload", "Expected JSON object")

        current_user_id = int(g.current_user["id"])
        role = str(g.current_user.get("role", "user"))
        credential_scope = str(payload.get("credential_scope", "personal")).strip().lower() or "personal"
        if credential_scope == "platform" and role != "superadmin":
            return json_error_fn(403, "forbidden", "Only superadmin can create platform credentials")

        owner_user_id = current_user_id if credential_scope == "personal" else int(payload.get("owner_user_id", current_user_id))
        try:
            created = create_credential_fn(
                config_getter().database_url,
                owner_user_id=owner_user_id,
                credential_scope=credential_scope,
                provider_slug=str(payload.get("provider", "openai_compatible")).strip().lower(),
                display_name=str(payload.get("display_name", "")).strip() or "credential",
                api_base_url=str(payload.get("api_base_url", "")).strip() or None,
                api_key=str(payload.get("api_key", "")).strip(),
                encryption_key=config_getter().model_credentials_encryption_key,
                created_by_user_id=current_user_id,
            )
        except ValueError as exc:
            return json_error_fn(400, str(exc), "Invalid credential payload")

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=current_user_id,
            event_type="credential.created",
            target_type="credential",
            target_id=str(created["id"]),
            payload={"owner_user_id": owner_user_id, "credential_scope": credential_scope},
        )
        return jsonify({"credential": serialize_credential_fn(created)}), 201

    @bp.delete("/v1/modelops/credentials/<credential_id>")
    @require_role("user")
    def delete_modelops_credential_route(credential_id: str):
        try:
            revoked = revoke_credential_fn(
                config_getter().database_url,
                credential_id=credential_id,
                owner_user_id=int(g.current_user["id"]),
            )
        except ValueError:
            return json_error_fn(400, "invalid_credential_id", "credential_id must be a UUID")

        if revoked is None:
            return json_error_fn(404, "credential_not_found", "Credential not found")

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="credential.revoked",
            target_type="credential",
            target_id=credential_id,
            payload={},
        )
        return jsonify({"credential": serialize_credential_fn(revoked)}), 200
