from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_bootstrap_registers_product_domains_without_legacy_chat_routes() -> None:
    bootstrap_source = (PROJECT_ROOT / "backend" / "app" / "bootstrap.py").read_text(encoding="utf-8")
    routes_init_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "__init__.py").read_text(encoding="utf-8")

    assert "from .api.http.playgrounds import bp as playgrounds_bp" in bootstrap_source
    assert "from .api.http.agent_projects import bp as agent_projects_bp" in bootstrap_source
    assert "from .api.http.platform import bp as platform_bp" in bootstrap_source
    assert "from .api.http.context import bp as context_bp" in bootstrap_source
    assert "from .routes import chat" not in bootstrap_source
    assert "from .routes import platform as platform_routes" not in bootstrap_source
    assert "from .routes import context as context_routes" not in bootstrap_source
    assert '"chat"' not in routes_init_source


def test_frontend_routes_point_to_feature_domain_pages() -> None:
    routes_source = (PROJECT_ROOT / "frontend" / "src" / "routes" / "appRoutes.tsx").read_text(encoding="utf-8")

    assert '../features/playgrounds/pages/PlaygroundsHomePage' in routes_source
    assert '../features/playgrounds/pages/ChatPlaygroundPage' in routes_source
    assert '../features/playgrounds/pages/KnowledgePlaygroundPage' in routes_source
    assert '../features/platform-control/pages/PlatformControlPage' in routes_source
    assert '../features/platform-control/pages/PlatformProvidersPage' in routes_source
    assert '../features/platform-control/pages/PlatformProviderCreatePage' in routes_source
    assert '../features/platform-control/pages/PlatformProviderDetailPage' in routes_source
    assert '../features/platform-control/pages/PlatformDeploymentsPage' in routes_source
    assert '../features/platform-control/pages/PlatformDeploymentCreatePage' in routes_source
    assert '../features/platform-control/pages/PlatformDeploymentDetailPage' in routes_source
    assert '../features/context-management/pages/ContextKnowledgeBasesPage' in routes_source
    assert '../features/context-management/pages/ContextKnowledgeBaseCreatePage' in routes_source
    assert '../features/context-management/pages/ContextKnowledgeBaseDetailPage' in routes_source
    assert '../pages/PlatformControlPage' not in routes_source
    assert '../pages/ContextKnowledgeBasesPage' not in routes_source


def test_playgrounds_service_does_not_depend_on_legacy_chat_or_knowledge_orchestrators() -> None:
    service_source = (PROJECT_ROOT / "backend" / "app" / "application" / "playgrounds_service.py").read_text(encoding="utf-8")

    assert "chat_conversations" not in service_source
    assert "knowledge_chat_service" not in service_source


def test_platform_and_context_routes_are_shims_to_api_http_modules() -> None:
    platform_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "platform.py").read_text(encoding="utf-8")
    context_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "context.py").read_text(encoding="utf-8")

    assert "from ..api.http.platform import bp" in platform_route_source
    assert "from ..api.http.context import bp" in context_route_source
