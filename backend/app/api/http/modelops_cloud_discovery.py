from __future__ import annotations

from flask import g, jsonify, request

from ...authz import require_role
from ...services.modelops_common import ModelOpsError


def register_modelops_cloud_discovery_routes(
    bp,
    *,
    config_getter,
    json_error_fn,
    discover_cloud_provider_models_fn,
):
    @bp.get("/v1/modelops/discovery/cloud")
    @require_role("user")
    def discover_modelops_cloud_models_route():
        try:
            config = config_getter()
            payload = discover_cloud_provider_models_fn(
                config.database_url,
                config=config,
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                provider=request.args.get("provider", ""),
                credential_id=request.args.get("credential_id", ""),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(payload), 200
