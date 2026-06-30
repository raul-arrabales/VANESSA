from __future__ import annotations

from typing import Any

from ..services.catalog_service import list_catalog_agents


def list_published_apps(database_url: str) -> list[dict[str, Any]]:
    apps: list[dict[str, Any]] = []
    for agent in list_catalog_agents(database_url):
        if agent.get("agent_kind") != "user":
            continue
        if not bool(agent.get("published", False)):
            continue
        spec = agent.get("spec") if isinstance(agent.get("spec"), dict) else {}
        if str(spec.get("channel_type") or "").strip().lower() != "vanessa_webapp":
            continue
        if str(spec.get("interface_type") or "").strip().lower() != "chat":
            continue
        apps.append(
            {
                "id": str(agent.get("id", "")),
                "agent_id": str(agent.get("id", "")),
                "name": str(spec.get("name", "")).strip(),
                "description": str(spec.get("description", "")).strip(),
                "interface_type": "chat",
                "channel_type": "vanessa_webapp",
                "agent_type": str(spec.get("agent_type") or "workflow"),
                "workflow_execution_mode": str(spec.get("workflow_execution_mode") or "one_time"),
                "published_at": agent.get("published_at"),
                "updated_at": agent.get("updated_at"),
            }
        )
    return apps


def get_published_app(database_url: str, *, app_id: str) -> dict[str, Any] | None:
    for app in list_published_apps(database_url):
        if app["id"] == app_id:
            return app
    return None
