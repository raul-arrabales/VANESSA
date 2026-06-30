from __future__ import annotations

from ..services.catalog_service import list_catalog_agents
from ..services.user_agent_specs import serialize_user_agent_spec


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
        normalized_spec = serialize_user_agent_spec(spec)
        apps.append(
            {
                "id": str(agent.get("id", "")),
                "agent_id": str(agent.get("id", "")),
                "name": normalized_spec["name"].strip(),
                "description": normalized_spec["description"].strip(),
                "interface_type": normalized_spec["interface_type"],
                "channel_type": normalized_spec["channel_type"],
                "agent_type": normalized_spec["agent_type"],
                "workflow_execution_mode": normalized_spec["workflow_execution_mode"],
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
