from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, Response, g, jsonify, request

from .auth_tokens import decode_access_token
from .config import AuthConfig
from .db import get_connection
from .repositories.users import find_user_by_id
from .services import auth_request_context, auth_runtime, system_health
from .services.platform_service import get_active_capability_statuses
from .services.platform_types import PlatformControlPlaneError

_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5
_GENERATED_DIR = Path(__file__).resolve().parent / "generated"
_ARCHITECTURE_JSON_PATH = _GENERATED_DIR / "architecture.json"
_ARCHITECTURE_SVG_PATH = _GENERATED_DIR / "architecture.svg"


def configure_request_context(app: Flask) -> None:
    @app.before_request
    def load_current_user_from_token() -> None:
        from . import app as app_module

        g.current_user = None
        g.auth_error = None

        current_user, auth_error = auth_request_context.resolve_current_user_from_auth_header(
            request.headers.get("Authorization", ""),
            ensure_auth_initialized_fn=app_module._ensure_auth_initialized,
            get_config_fn=app_module._get_config,
            decode_access_token_fn=decode_access_token,
            find_user_by_id_fn=app_module.find_user_by_id,
        )
        g.current_user = current_user
        g.auth_error = auth_error


def register_system_routes(app: Flask) -> None:
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "backend"}), 200

    @app.get("/system/health")
    def system_health_route():
        from . import app as app_module

        config = app_module._get_config()
        frontend_url = config.frontend_url.rstrip("/")
        backend_url = config.backend_url.rstrip("/")
        llm_url = config.llm_url.rstrip("/")
        llm_inference_runtime_url = config.llm_inference_runtime_url.rstrip("/")
        llm_embeddings_runtime_url = config.llm_embeddings_runtime_url.rstrip("/")
        agent_engine_url = config.agent_engine_url.rstrip("/")
        sandbox_url = config.sandbox_url.rstrip("/")
        mcp_gateway_url = config.mcp_gateway_url.rstrip("/")
        kws_url = config.kws_url.rstrip("/")
        weaviate_url = config.weaviate_url.rstrip("/")
        llama_cpp_url = config.llama_cpp_url.rstrip("/")
        qdrant_url = config.qdrant_url.rstrip("/")

        services = [
            {"service": "Frontend", "container": "frontend", "target": config.frontend_url, "reachable": app_module._http_json_ok(frontend_url + "/")},
            {"service": "Backend", "container": "backend", "target": config.backend_url, "reachable": app_module._http_json_ok(backend_url + "/health")},
            {"service": "LLM API", "container": "llm", "target": config.llm_url, "reachable": app_module._http_json_ok(llm_url + "/health")},
            {"service": "LLM Runtime Inference", "container": "llm_runtime_inference", "target": config.llm_inference_runtime_url, "reachable": app_module._http_json_ok(llm_inference_runtime_url + "/health")},
            {"service": "LLM Runtime Embeddings", "container": "llm_runtime_embeddings", "target": config.llm_embeddings_runtime_url, "reachable": app_module._http_json_ok(llm_embeddings_runtime_url + "/health")},
            {"service": "Agent Engine", "container": "agent_engine", "target": config.agent_engine_url, "reachable": app_module._http_json_ok(agent_engine_url + "/health")},
            {"service": "Sandbox", "container": "sandbox", "target": config.sandbox_url, "reachable": app_module._http_json_ok(sandbox_url + "/health")},
            {"service": "KWS", "container": "kws", "target": config.kws_url, "reachable": app_module._http_json_ok(kws_url + "/health")},
            {"service": "Weaviate", "container": "weaviate", "target": config.weaviate_url, "reachable": app_module._http_json_ok(weaviate_url + "/v1/.well-known/ready")},
            {"service": "PostgreSQL", "container": "postgres", "target": "postgresql", "reachable": app_module._postgres_ok(config.database_url)},
        ]
        if config.llama_cpp_url.strip():
            services.insert(4, {"service": "llama.cpp", "container": "llama_cpp", "target": config.llama_cpp_url, "reachable": app_module._http_json_ok(llama_cpp_url + "/v1/models")})
        if config.qdrant_url.strip():
            services.insert(len(services) - 1, {"service": "Qdrant", "container": "qdrant", "target": config.qdrant_url, "reachable": app_module._http_json_ok(qdrant_url + "/healthz")})
        if config.mcp_gateway_url.strip():
            services.insert(6, {"service": "MCP Gateway", "container": "mcp_gateway", "target": config.mcp_gateway_url, "reachable": app_module._http_json_ok(mcp_gateway_url + "/health")})

        response_payload: dict[str, Any] = {
            "status": "ok" if all(service["reachable"] for service in services) else "degraded",
            "services": services,
        }
        try:
            response_payload["platform"] = {"capabilities": app_module.get_active_capability_statuses(config.database_url, config)}
        except PlatformControlPlaneError as exc:
            response_payload["platform"] = {"error": exc.code, "message": exc.message}
        except Exception:
            response_payload["platform"] = {
                "error": "platform_health_unavailable",
                "message": "Platform capability health is currently unavailable",
            }
        return jsonify(response_payload), 200

    @app.get("/system/architecture")
    def system_architecture():
        try:
            payload = system_health.load_architecture_payload(_ARCHITECTURE_JSON_PATH)
        except (FileNotFoundError, ValueError):
            return jsonify({
                "error": "architecture_unavailable",
                "message": "Architecture graph artifact not available. Run: python scripts/generate_architecture.py --write",
            }), 503
        return jsonify(payload), 200

    @app.get("/system/architecture.svg")
    def system_architecture_svg():
        if not _ARCHITECTURE_SVG_PATH.exists():
            return jsonify({
                "error": "architecture_unavailable",
                "message": "Architecture SVG artifact not available. Run: python scripts/generate_architecture.py --write",
            }), 503
        return Response(_ARCHITECTURE_SVG_PATH.read_text(encoding="utf-8"), mimetype="image/svg+xml")


def register_http_blueprints(app: Flask) -> None:
    from .api.http.agent_projects import bp as agent_projects_bp
    from .api.http.catalog import bp as catalog_bp
    from .api.http.context import bp as context_bp
    from .api.http.playgrounds import bp as playgrounds_bp
    from .api.http.platform import bp as platform_bp
    from .api.http.registry import bp as registry_bp
    from .api.http.registry_models import bp as registry_models_bp
    from .routes import auth as auth_routes
    from .routes import auth_legacy_routes
    from .routes import content as content_routes
    from .routes import executions as executions_routes
    from .routes import model_inference_v1 as model_inference_v1_routes
    from .routes import modelops as modelops_routes
    from .routes import policy as policy_routes
    from .routes import quotes_v1 as quotes_v1_routes
    from .routes import runtime as runtime_routes
    from .routes import system as system_routes
    from .routes import voice_legacy_routes

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(auth_legacy_routes.bp)
    app.register_blueprint(content_routes.bp)
    app.register_blueprint(system_routes.bp)
    app.register_blueprint(registry_models_bp)
    app.register_blueprint(registry_bp)
    app.register_blueprint(policy_routes.bp)
    app.register_blueprint(quotes_v1_routes.bp)
    app.register_blueprint(runtime_routes.bp)
    app.register_blueprint(executions_routes.bp)
    app.register_blueprint(modelops_routes.bp)
    app.register_blueprint(model_inference_v1_routes.bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(context_bp)
    app.register_blueprint(agent_projects_bp)
    app.register_blueprint(playgrounds_bp)
    app.register_blueprint(voice_legacy_routes.bp)
