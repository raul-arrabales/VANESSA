from __future__ import annotations

from flask import g, jsonify, request

from ...application.modelops_access_service import build_scope_assignment_request
from ...authz import require_role
from ...services.modelops_common import ModelOpsError


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
        try:
            assignment_request = build_scope_assignment_request(request.get_json(silent=True))
            saved = upsert_scope_assignment_fn(
                config_getter().database_url,
                scope=str(assignment_request["scope"]),
                model_ids=list(assignment_request["model_ids"]),
                updated_by_user_id=int(g.current_user["id"]),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="model.sharing_updated",
            target_type="model_scope_assignment",
            target_id=str(assignment_request["scope"]),
            payload={"model_ids": saved.get("model_ids") or []},
        )
        return jsonify({"assignment": serialize_assignment_fn(saved)}), 200
