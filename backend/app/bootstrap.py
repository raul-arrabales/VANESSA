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

_CORE_SYSTEM_SERVICE_SPECS: tuple[dict[str, str], ...] = (
    {"service": "Frontend", "container": "frontend", "config_attr": "frontend_url", "health_path": "/"},
    {"service": "Backend", "container": "backend", "config_attr": "backend_url", "health_path": "/health"},
    {"service": "LLM API", "container": "llm", "config_attr": "llm_url", "health_path": "/health"},
    {
        "service": "LLM Runtime Inference",
        "container": "llm_runtime_inference",
        "config_attr": "llm_inference_runtime_url",
        "health_path": "/health",
    },
    {
        "service": "LLM Runtime Embeddings",
        "container": "llm_runtime_embeddings",
        "config_attr": "llm_embeddings_runtime_url",
        "health_path": "/health",
    },
    {"service": "Agent Engine", "container": "agent_engine", "config_attr": "agent_engine_url", "health_path": "/health"},
    {"service": "Sandbox", "container": "sandbox", "config_attr": "sandbox_url", "health_path": "/health"},
    {"service": "Weaviate", "container": "weaviate", "config_attr": "weaviate_url", "health_path": "/v1/.well-known/ready"},
)

def _service_health_entry(config: AuthConfig, *, service: str, container: str, config_attr: str, health_path: str) -> dict[str, Any]:
    from . import app as app_module

    target = str(getattr(config, config_attr)).strip()
    normalized_target = target.rstrip("/")
    return {
        "service": service,
        "container": container,
        "target": target,
        "reachable": app_module._http_json_ok(normalized_target + health_path),
    }


def _build_system_health_services(config: AuthConfig) -> list[dict[str, Any]]:
    services = [
        _service_health_entry(
            config,
            service=spec["service"],
            container=spec["container"],
            config_attr=spec["config_attr"],
            health_path=spec["health_path"],
        )
        for spec in _CORE_SYSTEM_SERVICE_SPECS
    ]
    services.insert(
        6,
        _service_health_entry(
            config,
            service="MCP Gateway",
            container="mcp_gateway",
            config_attr="mcp_gateway_url",
            health_path="/health",
        ),
    )
    if config.web_search_enabled:
        services.insert(
            7,
            _service_health_entry(
                config,
                service="SearXNG Web Search",
                container="searxng",
                config_attr="web_search_url",
                health_path="/",
            ),
        )
    if config.image_analysis_url.strip():
        services.insert(
            8,
            _service_health_entry(
                config,
                service="Image Analysis",
                container="image_analysis",
                config_attr="image_analysis_url",
                health_path="/health",
            ),
        )
    if config.image_generation_url.strip():
        services.insert(
            9,
            _service_health_entry(
                config,
                service="Image Generation",
                container="image_generation",
                config_attr="image_generation_url",
                health_path="/health",
            ),
        )
    if config.kws_enabled:
        services.insert(
            len(services) - 2,
            _service_health_entry(
                config,
                service="KWS",
                container="kws",
                config_attr="kws_url",
                health_path="/health",
            ),
        )
    if config.llama_cpp_url.strip():
        services.insert(
            4,
            _service_health_entry(
                config,
                service="llama.cpp",
                container="llama_cpp",
                config_attr="llama_cpp_url",
                health_path="/v1/models",
            ),
        )
    if config.qdrant_url.strip():
        services.insert(
            len(services) - 1,
            _service_health_entry(
                config,
                service="Qdrant",
                container="qdrant",
                config_attr="qdrant_url",
                health_path="/healthz",
            ),
        )
    services.append({"service": "PostgreSQL", "container": "postgres", "target": "postgresql", "reachable": False})
    return services


def configure_request_context(app: Flask) -> None:
    @app.before_request
    def load_current_user_from_token() -> None:
        from . import app as app_module

        g.current_user = None
        g.auth_error = None
        g.backend_initialized = bool(app_module._ensure_backend_initialized())

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
        ready = bool(getattr(g, "backend_initialized", False))
        if not ready:
            return jsonify(
                {
                    "status": "initializing",
                    "service": "backend",
                    "ready": False,
                    "message": "Backend initialization is still in progress.",
                }
            ), 503
        return jsonify({"status": "ok", "service": "backend"}), 200

    @app.get("/system/health")
    def system_health_route():
        from . import app as app_module

        config = app_module._get_config()
        services = _build_system_health_services(config)
        services[-1]["reachable"] = app_module._postgres_ok(config.database_url)

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
    from .api.http.apps import bp as apps_bp
    from .api.http.agent_projects import bp as agent_projects_bp
    from .api.http.catalog import bp as catalog_bp
    from .api.http.content import bp as content_bp
    from .api.http.context import bp as context_bp
    from .api.http.executions import bp as executions_bp
    from .api.http.modelops import bp as modelops_bp
    from .api.http.policy import bp as policy_bp
    from .api.http.playgrounds import bp as playgrounds_bp
    from .api.http.platform import bp as platform_bp
    from .api.http.quotes import bp as quotes_bp
    from .api.http.registry import bp as registry_bp
    from .api.http.registry_models import bp as registry_models_bp
    from .api.http.runtime import bp as runtime_bp
    from .api.http.system_logs import bp as system_logs_bp
    from .routes import auth as auth_routes
    from .routes import auth_legacy_routes
    from .routes import model_inference_v1 as model_inference_v1_routes
    from .routes import system as system_routes
    from .routes import voice_legacy_routes

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(auth_legacy_routes.bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(system_routes.bp)
    app.register_blueprint(registry_models_bp)
    app.register_blueprint(registry_bp)
    app.register_blueprint(policy_bp)
    app.register_blueprint(quotes_bp)
    app.register_blueprint(runtime_bp)
    app.register_blueprint(system_logs_bp)
    app.register_blueprint(executions_bp)
    app.register_blueprint(modelops_bp)
    app.register_blueprint(model_inference_v1_routes.bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(context_bp)
    app.register_blueprint(agent_projects_bp)
    app.register_blueprint(playgrounds_bp)
    app.register_blueprint(voice_legacy_routes.bp)
