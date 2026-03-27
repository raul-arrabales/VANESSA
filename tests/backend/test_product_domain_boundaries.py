from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_bootstrap_registers_product_domains_without_legacy_chat_routes() -> None:
    bootstrap_source = (PROJECT_ROOT / "backend" / "app" / "bootstrap.py").read_text(encoding="utf-8")
    routes_init_source = (PROJECT_ROOT / "backend" / "app" / "routes" / "__init__.py").read_text(encoding="utf-8")

    assert "from .api.http.playgrounds import bp as playgrounds_bp" in bootstrap_source
    assert "from .api.http.agent_projects import bp as agent_projects_bp" in bootstrap_source
    assert "from .routes import chat" not in bootstrap_source
    assert '"chat"' not in routes_init_source


def test_frontend_routes_point_to_feature_domain_pages() -> None:
    routes_source = (PROJECT_ROOT / "frontend" / "src" / "routes" / "appRoutes.tsx").read_text(encoding="utf-8")

    assert '../features/playgrounds/pages/PlaygroundsHomePage' in routes_source
    assert '../features/playgrounds/pages/ChatPlaygroundPage' in routes_source
    assert '../features/playgrounds/pages/KnowledgePlaygroundPage' in routes_source
