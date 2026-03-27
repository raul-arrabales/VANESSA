from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_bootstrap_registers_canonical_http_domains() -> None:
    bootstrap_source = (PROJECT_ROOT / "backend" / "app" / "bootstrap.py").read_text(encoding="utf-8")

    assert "from .api.http.playgrounds import bp as playgrounds_bp" in bootstrap_source
    assert "from .api.http.agent_projects import bp as agent_projects_bp" in bootstrap_source
    assert "from .api.http.modelops import bp as modelops_bp" in bootstrap_source
    assert "from .api.http.platform import bp as platform_bp" in bootstrap_source
    assert "from .api.http.context import bp as context_bp" in bootstrap_source
    assert "from .api.http.catalog import bp as catalog_bp" in bootstrap_source
    assert "from .api.http.registry import bp as registry_bp" in bootstrap_source
    assert "from .api.http.registry_models import bp as registry_models_bp" in bootstrap_source
    assert "from .api.http.content import bp as content_bp" in bootstrap_source
    assert "from .api.http.runtime import bp as runtime_bp" in bootstrap_source
    assert "from .api.http.executions import bp as executions_bp" in bootstrap_source
    assert "from .api.http.policy import bp as policy_bp" in bootstrap_source
    assert "from .api.http.quotes import bp as quotes_bp" in bootstrap_source
    assert "from .routes import chat" not in bootstrap_source
    assert "from .routes import platform as platform_routes" not in bootstrap_source
    assert "from .routes import context as context_routes" not in bootstrap_source
    assert "from .routes import modelops as modelops_routes" not in bootstrap_source
    assert "from .routes import catalog as catalog_routes" not in bootstrap_source
    assert "from .routes import registry as registry_routes" not in bootstrap_source
    assert "from .routes import registry_models as registry_models_routes" not in bootstrap_source
    assert "from .routes import runtime as runtime_routes" not in bootstrap_source
    assert "from .routes import executions as executions_routes" not in bootstrap_source
    assert "from .routes import policy as policy_routes" not in bootstrap_source
    assert "from .routes import quotes_v1 as quotes_v1_routes" not in bootstrap_source
    assert "from .routes import content as content_routes" not in bootstrap_source


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
    assert '../features/agent-builder/pages/AgentBuilderProjectsPage' in routes_source
    assert '../features/agent-builder/pages/AgentProjectDetailPage' in routes_source
    assert '../features/catalog-admin/pages/CatalogControlPage' in routes_source
    assert '../pages/PlatformControlPage' not in routes_source
    assert '../pages/ContextKnowledgeBasesPage' not in routes_source
    assert '../pages/CatalogControlPage' not in routes_source


def test_playgrounds_service_does_not_depend_on_legacy_chat_or_knowledge_orchestrators() -> None:
    service_source = (PROJECT_ROOT / "backend" / "app" / "application" / "playgrounds_service.py").read_text(encoding="utf-8")

    assert "chat_conversations" not in service_source
    assert "knowledge_chat_service" not in service_source


def test_platform_and_context_routes_are_shims_to_api_http_modules() -> None:
    platform_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "platform.py").read_text(encoding="utf-8")
    context_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "context.py").read_text(encoding="utf-8")
    modelops_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops.py").read_text(encoding="utf-8")
    modelops_models_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops_models_routes.py").read_text(encoding="utf-8")
    modelops_credentials_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops_credentials_routes.py").read_text(encoding="utf-8")
    modelops_access_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops_access_routes.py").read_text(encoding="utf-8")
    modelops_local_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops_local_routes.py").read_text(encoding="utf-8")
    modelops_common_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "modelops_route_common.py").read_text(encoding="utf-8")
    catalog_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "catalog.py").read_text(encoding="utf-8")
    registry_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "registry.py").read_text(encoding="utf-8")
    registry_models_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "registry_models.py").read_text(encoding="utf-8")
    runtime_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "runtime.py").read_text(encoding="utf-8")
    executions_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "executions.py").read_text(encoding="utf-8")
    policy_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "policy.py").read_text(encoding="utf-8")
    quotes_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "quotes_v1.py").read_text(encoding="utf-8")
    content_route_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "content.py").read_text(encoding="utf-8")

    assert "from ..api.http.platform import bp" in platform_route_source
    assert "from ..api.http.context import bp" in context_route_source
    assert "from ..api.http.modelops import" in modelops_route_source
    assert "from ..api.http.modelops_models import register_modelops_models_routes" in modelops_models_route_source
    assert "from ..api.http.modelops_credentials import register_modelops_credentials_routes" in modelops_credentials_route_source
    assert "from ..api.http.modelops_access import register_modelops_access_routes" in modelops_access_route_source
    assert "from ..api.http.modelops_local import register_modelops_local_routes" in modelops_local_route_source
    assert "from ..api.http.modelops_common import" in modelops_common_route_source
    assert "from ..api.http.catalog import bp" in catalog_route_source
    assert "from ..api.http.registry import bp" in registry_route_source
    assert "from ..api.http.registry_models import bp" in registry_models_route_source
    assert "from ..api.http.runtime import" in runtime_route_source
    assert "from ..api.http.executions import" in executions_route_source
    assert "from ..api.http.policy import" in policy_route_source
    assert "from ..api.http.quotes import" in quotes_route_source
    assert "from ..api.http.content import" in content_route_source


def test_agent_projects_service_uses_application_catalog_contract() -> None:
    source = (PROJECT_ROOT / "backend" / "app" / "application" / "agent_projects_service.py").read_text(encoding="utf-8")

    assert "from .catalog_management_service import create_catalog_agent, update_catalog_agent" in source
    assert "services.catalog_service" not in source


def test_modelops_http_is_canonical_and_application_owned() -> None:
    http_source = (PROJECT_ROOT / "backend" / "app" / "api" / "http" / "modelops.py").read_text(encoding="utf-8")
    models_service_source = (
        PROJECT_ROOT / "backend" / "app" / "application" / "modelops_models_service.py"
    ).read_text(encoding="utf-8")
    testing_service_source = (
        PROJECT_ROOT / "backend" / "app" / "application" / "modelops_testing_service.py"
    ).read_text(encoding="utf-8")

    assert "from ...application.modelops_models_service import" in http_source
    assert "from ...application.modelops_testing_service import" in http_source
    assert "from ...routes import modelops" not in http_source
    assert "from ..services.modelops_lifecycle import" in models_service_source
    assert "from ..services.modelops_testing import" in testing_service_source


def test_remaining_edge_http_domains_are_canonical_and_application_owned() -> None:
    executions_http_source = (
        PROJECT_ROOT / "backend" / "app" / "api" / "http" / "executions.py"
    ).read_text(encoding="utf-8")
    runtime_http_source = (
        PROJECT_ROOT / "backend" / "app" / "api" / "http" / "runtime.py"
    ).read_text(encoding="utf-8")
    policy_http_source = (
        PROJECT_ROOT / "backend" / "app" / "api" / "http" / "policy.py"
    ).read_text(encoding="utf-8")
    quotes_http_source = (
        PROJECT_ROOT / "backend" / "app" / "api" / "http" / "quotes.py"
    ).read_text(encoding="utf-8")

    assert "from ...application.execution_management_service import" in executions_http_source
    assert "from ...application.runtime_profile_service_app import" in runtime_http_source
    assert "from ...application.policy_management_service import" in policy_http_source
    assert "from ...application.quote_management_service_app import" in quotes_http_source
