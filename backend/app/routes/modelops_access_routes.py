from __future__ import annotations

from flask import g, jsonify, request

from ..authz import require_role


def register_modelops_access_routes(
    bp,
    *,
    config_getter,
    json_error_fn,
    list_scope_assignments_fn,
    upsert_scope_assignment_fn,
    serialize_assignment_fn,
    append_audit_event_fn,
):
    @bp.get("/v1/modelops/sharing")
    @require_role("admin")
    def list_modelops_sharing_route():
        rows = list_scope_assignments_fn(config_getter().database_url)
        return jsonify({"assignments": [serialize_assignment_fn(row) for row in rows]}), 200

    @bp.put("/v1/modelops/sharing")
    @require_role("admin")
    def update_modelops_sharing_route():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return json_error_fn(400, "invalid_payload", "Expected JSON object")

        scope = str(payload.get("scope", "")).strip().lower()
        model_ids = payload.get("model_ids")
        if not isinstance(model_ids, list):
            return json_error_fn(400, "invalid_model_ids", "model_ids must be an array")

        try:
            saved = upsert_scope_assignment_fn(
                config_getter().database_url,
                scope=scope,
                model_ids=[str(item) for item in model_ids],
                updated_by_user_id=int(g.current_user["id"]),
            )
        except ValueError:
            return json_error_fn(400, "invalid_scope", "scope must be user, admin, or superadmin")

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="model.sharing_updated",
            target_type="model_scope_assignment",
            target_id=scope,
            payload={"model_ids": saved.get("model_ids") or []},
        )
        return jsonify({"assignment": serialize_assignment_fn(saved)}), 200
