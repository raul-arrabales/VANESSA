from __future__ import annotations

from flask import g, jsonify, request

from ...application.modelops_models_service import (
    parse_capability_key,
    parse_eligible_only,
    parse_limit,
    parse_update_credential_request,
)
from ...application.modelops_testing_service import parse_model_test_request, parse_test_limit, parse_validation_request
from ...authz import require_role
from ...services.modelops_common import ModelOpsError


def register_modelops_models_routes(
    bp,
    *,
    config_getter,
    json_error_fn,
    list_models_fn,
    create_model_fn,
    get_model_detail_fn,
    get_model_usage_fn,
    get_model_validations_fn,
    register_existing_model_fn,
    validate_model_fn,
    get_model_tests_fn,
    get_model_test_runtimes_fn,
    run_model_test_fn,
    activate_model_fn,
    deactivate_model_fn,
    unregister_model_fn,
    update_model_credential_fn,
    delete_model_fn,
):
    @bp.get("/v1/modelops/models")
    @require_role("user")
    def list_modelops_models_route():
        try:
            models = list_models_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                require_active=parse_eligible_only(request.args.get("eligible")),
                capability_key=parse_capability_key(request.args.get("capability")),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"models": models}), 200

    @bp.post("/v1/modelops/models")
    @require_role("user")
    def create_modelops_model_route():
        try:
            model = create_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                payload=request.get_json(silent=True),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 201

    @bp.get("/v1/modelops/models/<model_id>")
    @require_role("user")
    def get_modelops_model_route(model_id: str):
        try:
            model = get_model_detail_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.get("/v1/modelops/models/<model_id>/usage")
    @require_role("user")
    def get_modelops_model_usage_route(model_id: str):
        try:
            payload = get_model_usage_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(payload), 200

    @bp.get("/v1/modelops/models/<model_id>/validations")
    @require_role("user")
    def get_modelops_model_validations_route(model_id: str):
        try:
            payload = get_model_validations_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
                limit=parse_limit(request.args.get("limit"), default=20, minimum=1, maximum=100),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(payload), 200

    @bp.post("/v1/modelops/models/<model_id>/register")
    @require_role("user")
    def register_modelops_model_route(model_id: str):
        try:
            model = register_existing_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.post("/v1/modelops/models/<model_id>/validate")
    @require_role("admin")
    def validate_modelops_model_route(model_id: str):
        try:
            result = validate_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
                trigger_reason="manual_after_test",
                test_run_id=parse_validation_request(request.get_json(silent=True)),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(result), 200

    @bp.get("/v1/modelops/models/<model_id>/tests")
    @require_role("admin")
    def get_modelops_model_tests_route(model_id: str):
        try:
            payload = get_model_tests_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
                limit=parse_test_limit(request.args.get("limit")),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(payload), 200

    @bp.get("/v1/modelops/models/<model_id>/test-runtimes")
    @require_role("superadmin")
    def get_modelops_model_test_runtimes_route(model_id: str):
        try:
            payload = get_model_test_runtimes_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(payload), 200

    @bp.post("/v1/modelops/models/<model_id>/test")
    @require_role("admin")
    def test_modelops_model_route(model_id: str):
        try:
            inputs, provider_instance_id = parse_model_test_request(request.get_json(silent=True))
            result = run_model_test_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
                inputs=inputs,
                provider_instance_id=provider_instance_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify(result), 200

    @bp.post("/v1/modelops/models/<model_id>/activate")
    @require_role("user")
    def activate_modelops_model_route(model_id: str):
        try:
            model = activate_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.post("/v1/modelops/models/<model_id>/deactivate")
    @require_role("user")
    def deactivate_modelops_model_route(model_id: str):
        try:
            model = deactivate_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.post("/v1/modelops/models/<model_id>/unregister")
    @require_role("user")
    def unregister_modelops_model_route(model_id: str):
        try:
            model = unregister_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.patch("/v1/modelops/models/<model_id>/credential")
    @require_role("user")
    def update_modelops_model_credential_route(model_id: str):
        try:
            model = update_model_credential_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
                credential_id=parse_update_credential_request(request.get_json(silent=True)),
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"model": model}), 200

    @bp.delete("/v1/modelops/models/<model_id>")
    @require_role("user")
    def delete_modelops_model_route(model_id: str):
        try:
            delete_model_fn(
                config_getter().database_url,
                config=config_getter(),
                actor_user_id=int(g.current_user["id"]),
                actor_role=str(g.current_user.get("role", "user")),
                model_id=model_id,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        return jsonify({"deleted": True, "model_id": model_id}), 200
