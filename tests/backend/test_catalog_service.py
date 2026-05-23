from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import catalog_service  # noqa: E402
from app.services import catalog_tool_backends  # noqa: E402
from app.services import tool_registry_bootstrap  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def test_catalog_defaults_expose_backend_owned_agent_runtime_prompts():
    defaults = catalog_service.get_catalog_defaults()

    assert defaults["agent"]["runtime_prompts"] == catalog_service.default_agent_runtime_prompts()


def test_mcp_server_status_serializes_as_validation_status():
    status = catalog_service._serialize_mcp_validation_status(
        {
            "runtime_status": "success",
            "validated_version": "v2",
            "last_validated_at": "2026-01-01T00:00:00+00:00",
            "validation_errors": [],
        },
        "v2",
    )

    assert status == {
        "last_validation_status": "success",
        "is_validation_current": True,
        "validated_version": "v2",
        "last_validated_at": "2026-01-01T00:00:00+00:00",
        "validation_errors": [],
    }


def test_coerce_mcp_server_spec_accepts_and_normalizes_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(catalog_service, "_ensure_unique_mcp_slug", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(catalog_service, "_ensure_tool_eligible_for_mcp", lambda *_args, **_kwargs: {})

    spec = catalog_service._coerce_mcp_server_spec(
        "ignored",
        {
            "name": "Web Search MCP",
            "slug": "web_search",
            "description": "Expose web search.",
            "backing_tool_id": "tool.web_search",
            "exposed_tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "metadata": {
                "category": "web_search",
                "capabilities": ["Web Search", "fresh_information", "web-search"],
                "local": False,
                "stateless": True,
                "sandboxed": False,
                "risk_level": "medium",
                "data_access": "public_web",
                "output_freshness": "fresh",
                "audit_level": "standard",
            },
            "authorization_policy": {},
            "enabled": True,
        },
        current_id=None,
    )

    assert spec["metadata"] == {
        "category": "web_search",
        "capabilities": ["web-search", "fresh-information"],
        "local": False,
        "stateless": True,
        "sandboxed": False,
        "risk_level": "medium",
        "data_access": "public_web",
        "output_freshness": "fresh",
        "audit_level": "standard",
    }


def test_coerce_mcp_server_spec_rejects_invalid_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(catalog_service, "_ensure_unique_mcp_slug", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(catalog_service, "_ensure_tool_eligible_for_mcp", lambda *_args, **_kwargs: {})

    with pytest.raises(catalog_service.CatalogError) as exc:
        catalog_service._coerce_mcp_server_spec(
            "ignored",
            {
                "name": "Web Search MCP",
                "slug": "web_search",
                "description": "Expose web search.",
                "backing_tool_id": "tool.web_search",
                "exposed_tool_name": "web_search",
                "input_schema": {},
                "output_schema": {},
                "metadata": {
                    "category": "web_search",
                    "capabilities": ["web-search"],
                    "local": "false",
                    "stateless": True,
                    "sandboxed": False,
                    "risk_level": "medium",
                    "data_access": "public_web",
                    "output_freshness": "fresh",
                    "audit_level": "standard",
                },
                "authorization_policy": {},
                "enabled": True,
            },
            current_id=None,
        )

    assert exc.value.code == "invalid_mcp_metadata"
    assert "metadata.local" in exc.value.message


def test_discover_authorized_mcp_servers_includes_metadata(monkeypatch: pytest.MonkeyPatch):
    metadata = {
        "category": "web_search",
        "capabilities": ["web-search"],
        "local": False,
        "stateless": True,
        "sandboxed": False,
        "risk_level": "medium",
        "data_access": "public_web",
        "output_freshness": "fresh",
        "audit_level": "standard",
    }
    monkeypatch.setattr(catalog_service, "list_user_group_ids", lambda *_args, **_kwargs: set())
    monkeypatch.setattr(
        catalog_service,
        "list_catalog_mcp_servers",
        lambda _db: [
            {
                "id": "mcp.web_search",
                "published_at": "2026-01-01T00:00:00+00:00",
                "spec": {
                    "slug": "web_search",
                    "exposed_tool_name": "web_search",
                    "description": "desc",
                    "input_schema": {},
                    "output_schema": {},
                    "backing_tool_id": "tool.web_search",
                    "metadata": metadata,
                    "authorization_policy": {
                        "agent_ids": ["*"],
                        "agent_domains": ["*"],
                        "user_roles": ["*"],
                        "user_ids": ["*"],
                        "user_group_ids": ["*"],
                    },
                    "enabled": True,
                },
            }
        ],
    )

    discovered = catalog_service.discover_authorized_mcp_servers(
        "ignored",
        agent_id="agent.alpha",
        agent_domain="default",
        delegated_user_id=None,
        delegated_user_role=None,
    )

    assert discovered[0]["metadata"] == metadata


def test_builtin_mcp_servers_include_metadata_and_python_execution():
    web_search = tool_registry_bootstrap._BUILTIN_MCP_SERVERS["mcp.web_search"]
    python_exec = tool_registry_bootstrap._BUILTIN_MCP_SERVERS["mcp.python_exec"]

    assert web_search["metadata"]["category"] == "web_search"
    assert web_search["metadata"]["local"] is False
    assert python_exec["backing_tool_id"] == "tool.python_exec"
    assert python_exec["exposed_tool_name"] == "python_exec"
    assert python_exec["metadata"]["category"] == "code_execution"
    assert python_exec["metadata"]["risk_level"] == "high"


def _catalog_row(entity_id: str, entity_type: str, spec: dict[str, object]) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "current_spec": spec,
        "published_at": "2026-01-01T00:00:00+00:00",
    }


def test_list_catalog_tools_hides_image_tools_without_enabled_worker(monkeypatch: pytest.MonkeyPatch):
    rows = [
        _catalog_row("tool.web_search", "tool", tool_registry_bootstrap._BUILTIN_TOOLS["tool.web_search"]),
        _catalog_row("tool.image_license_plate_recognition", "tool", tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_license_plate_recognition"]),
        _catalog_row("tool.image_object_detection", "tool", tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_object_detection"]),
        _catalog_row("tool.image_captioning", "tool", tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_captioning"]),
    ]
    monkeypatch.setattr(catalog_service, "list_registry_entities", lambda _db, *, entity_type: rows if entity_type == "tool" else [])
    monkeypatch.setattr(catalog_service, "image_analysis_available_tasks", lambda _db, _config: {"license_plate_recognition"})

    tools = catalog_service.list_catalog_tools("ignored", config=SimpleNamespace())

    assert [tool["id"] for tool in tools] == ["tool.web_search", "tool.image_license_plate_recognition"]


def test_list_catalog_mcp_servers_hides_image_servers_without_enabled_worker(monkeypatch: pytest.MonkeyPatch):
    tool_rows = {
        "tool.image_license_plate_recognition": _catalog_row(
            "tool.image_license_plate_recognition",
            "tool",
            tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_license_plate_recognition"],
        ),
        "tool.image_object_detection": _catalog_row(
            "tool.image_object_detection",
            "tool",
            tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_object_detection"],
        ),
        "tool.image_captioning": _catalog_row(
            "tool.image_captioning",
            "tool",
            tool_registry_bootstrap._BUILTIN_TOOLS["tool.image_captioning"],
        ),
    }
    mcp_rows = [
        _catalog_row("mcp.image_license_plate_recognition", "mcp_server", tool_registry_bootstrap._BUILTIN_MCP_SERVERS["mcp.image_license_plate_recognition"]),
        _catalog_row("mcp.image_object_detection", "mcp_server", tool_registry_bootstrap._BUILTIN_MCP_SERVERS["mcp.image_object_detection"]),
        _catalog_row("mcp.image_captioning", "mcp_server", tool_registry_bootstrap._BUILTIN_MCP_SERVERS["mcp.image_captioning"]),
    ]
    monkeypatch.setattr(catalog_service, "list_registry_entities", lambda _db, *, entity_type: mcp_rows if entity_type == "mcp_server" else [])
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_rows.get(entity_id))
    monkeypatch.setattr(catalog_service, "image_analysis_available_tasks", lambda _db, _config: {"license_plate_recognition"})

    servers = catalog_service.list_catalog_mcp_servers("ignored", config=SimpleNamespace())

    assert [server["id"] for server in servers] == ["mcp.image_license_plate_recognition"]


def test_builtin_mcp_seed_reconciles_changed_specs(monkeypatch: pytest.MonkeyPatch):
    entities = {
        "mcp_server:mcp.web_search": {
            "entity_id": "mcp.web_search",
            "entity_type": "mcp_server",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "current_spec": {"name": "Old Web Search MCP"},
            "published_at": "2026-01-01T00:00:00+00:00",
        }
    }
    versions: list[dict[str, object]] = [{"entity_id": "mcp.web_search", "version": "v1"}]
    status_upserts: list[str] = []

    monkeypatch.setattr(tool_registry_bootstrap, "list_users", lambda _db, is_active=None: [{"id": 1, "role": "superadmin"}])
    monkeypatch.setattr(
        tool_registry_bootstrap,
        "find_registry_entity",
        lambda _db, *, entity_type, entity_id: entities.get(f"{entity_type}:{entity_id}"),
    )
    monkeypatch.setattr(
        tool_registry_bootstrap,
        "create_registry_entity",
        lambda _db, **kwargs: entities.setdefault(
            f"{kwargs['entity_type']}:{kwargs['entity_id']}",
            {
                "entity_id": kwargs["entity_id"],
                "entity_type": kwargs["entity_type"],
                "owner_user_id": kwargs["owner_user_id"],
                "visibility": kwargs["visibility"],
                "status": kwargs["status"],
                "current_version": None,
                "current_spec": None,
                "published_at": None,
            },
        ),
    )

    def _create_registry_version(_db, *, entity_id, version, spec_json, set_current, published):
        del set_current
        key = f"{'tool' if entity_id.startswith('tool.') else 'mcp_server'}:{entity_id}"
        entities[key]["current_version"] = version
        entities[key]["current_spec"] = spec_json
        entities[key]["published_at"] = "2026-01-01T00:00:00+00:00" if published else None
        versions.append({"entity_id": entity_id, "version": version})
        return {"entity_id": entity_id, "version": version, "spec_json": spec_json}

    monkeypatch.setattr(tool_registry_bootstrap, "create_registry_version", _create_registry_version)
    monkeypatch.setattr(tool_registry_bootstrap, "list_registry_versions", lambda _db, *, entity_id: [row for row in versions if row["entity_id"] == entity_id])
    monkeypatch.setattr(tool_registry_bootstrap, "upsert_tool_runtime_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        tool_registry_bootstrap,
        "upsert_mcp_server_status",
        lambda _db, *, mcp_server_id, **_kwargs: status_upserts.append(mcp_server_id),
    )

    assert tool_registry_bootstrap.ensure_builtin_tools("ignored") is True

    assert entities["mcp_server:mcp.web_search"]["current_version"] == "v2"
    assert entities["mcp_server:mcp.web_search"]["current_spec"]["metadata"]["category"] == "web_search"
    assert entities["mcp_server:mcp.python_exec"]["current_spec"]["metadata"]["category"] == "code_execution"
    assert "mcp.web_search" in status_upserts
    assert "mcp.python_exec" in status_upserts


def _knowledge_base_retrieval_tool_payload() -> dict[str, object]:
    return {
        "name": "Product Docs Retrieval",
        "description": "Retrieves relevant passages from Product Docs.",
        "input_schema": catalog_tool_backends.knowledge_base_retrieval_input_schema(),
        "output_schema": catalog_tool_backends.knowledge_base_retrieval_output_schema(),
        "safety_policy": {"timeout_seconds": 8, "network_access": False},
        "offline_compatible": True,
        "execution_backend": "knowledge_base_retrieval",
        "execution_config": {
            "knowledge_base_id": "kb-product-docs",
            "retrieval_defaults": {
                "top_k": 5,
                "search_method": "semantic",
                "query_preprocessing": "none",
            },
        },
        "permissions": {},
    }


def test_tool_creation_options_include_retrieval_template_for_active_bound_knowledge_bases(monkeypatch: pytest.MonkeyPatch):
    runtime = {
        "capabilities": {
            "embeddings": {"provider_origin": "local"},
            "vector_store": {"provider_origin": "local"},
        }
    }
    knowledge_base = {
        "id": "kb-product-docs",
        "display_name": "Product Docs",
        "slug": "product-docs",
        "index_name": "kb_product_docs",
        "is_default": True,
    }
    monkeypatch.setattr(catalog_tool_backends, "get_active_platform_runtime", lambda _db, _config: runtime)
    monkeypatch.setattr(
        catalog_tool_backends,
        "list_active_runtime_knowledge_bases",
        lambda _runtime, *, database_url: {
            "knowledge_bases": [knowledge_base],
            "default_knowledge_base_id": "kb-product-docs",
            "selection_required": False,
            "configuration_message": None,
        },
    )

    options = catalog_service.get_catalog_tool_creation_options("ignored", config=SimpleNamespace())
    retrieval_option = next(item for item in options["execution_backends"] if item["execution_backend"] == "knowledge_base_retrieval")
    template = retrieval_option["templates_by_knowledge_base_id"]["kb-product-docs"]

    assert options["default_knowledge_base_id"] == "kb-product-docs"
    assert retrieval_option["requires_knowledge_base"] is True
    assert template["id"] == "tool.kb_retrieval.product-docs"
    assert template["name"] == "Product Docs Retrieval"
    assert template["execution_config"]["knowledge_base_id"] == "kb-product-docs"
    assert template["offline_compatible"] is True


def test_coerce_tool_spec_validates_knowledge_base_retrieval_config(monkeypatch: pytest.MonkeyPatch):
    missing_payload = _knowledge_base_retrieval_tool_payload()
    missing_payload["execution_config"] = {}

    with pytest.raises(catalog_service.CatalogError) as missing_exc:
        catalog_service._coerce_tool_spec("ignored", missing_payload, config=SimpleNamespace())

    assert missing_exc.value.code == "invalid_execution_config"

    unbound_payload = _knowledge_base_retrieval_tool_payload()
    monkeypatch.setattr(catalog_tool_backends, "active_bound_knowledge_bases", lambda *_args, **_kwargs: [])

    with pytest.raises(catalog_service.CatalogError) as unbound_exc:
        catalog_service._coerce_tool_spec("ignored", unbound_payload, config=SimpleNamespace())

    assert unbound_exc.value.code == "knowledge_base_not_bound"

    monkeypatch.setattr(
        catalog_tool_backends,
        "active_bound_knowledge_bases",
        lambda *_args, **_kwargs: [{"id": "kb-product-docs", "display_name": "Product Docs"}],
    )
    spec = catalog_service._coerce_tool_spec("ignored", unbound_payload, config=SimpleNamespace())

    assert spec["execution_backend"] == "knowledge_base_retrieval"
    assert spec["execution_config"]["knowledge_base_id"] == "kb-product-docs"


def test_validate_catalog_tool_reports_knowledge_base_binding(monkeypatch: pytest.MonkeyPatch):
    payload = _knowledge_base_retrieval_tool_payload()
    monkeypatch.setattr(
        catalog_tool_backends,
        "find_active_bound_knowledge_base",
        lambda *_args, **_kwargs: {"id": "kb-product-docs", "display_name": "Product Docs"},
    )

    runtime_checks, errors = catalog_service._validate_catalog_tool_definition(
        database_url="ignored",
        config=SimpleNamespace(),
        spec=payload,
    )

    assert errors == []
    assert runtime_checks["knowledge_base_id"] == "kb-product-docs"
    assert runtime_checks["knowledge_base_bound"] is True
    assert runtime_checks["knowledge_base_display_name"] == "Product Docs"
    assert runtime_checks["provider_reachable"] is True


def test_execute_catalog_tool_invokes_knowledge_base_retrieval_with_merged_defaults(monkeypatch: pytest.MonkeyPatch):
    payload = _knowledge_base_retrieval_tool_payload()
    tool_row = {
        "entity_id": "tool.kb_retrieval.product-docs",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": payload,
    }
    captured: dict[str, object] = {}
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)
    monkeypatch.setattr(
        catalog_tool_backends,
        "find_active_bound_knowledge_base",
        lambda *_args, **_kwargs: {"id": "kb-product-docs", "display_name": "Product Docs"},
    )
    monkeypatch.setattr(
        catalog_tool_backends,
        "query_knowledge_base",
        lambda _db, *, config, knowledge_base_id, payload: captured.update(
            {"knowledge_base_id": knowledge_base_id, "payload": payload}
        )
        or {
            "knowledge_base_id": knowledge_base_id,
            "retrieval": {
                "index": "kb_product_docs",
                "result_count": 1,
                "top_k": payload["top_k"],
                "search_method": payload["search_method"],
                "query_preprocessing": payload["query_preprocessing"],
            },
            "results": [{"chunk_id": "chunk-1", "text": "Relevant passage"}],
        },
    )

    result = catalog_service.execute_catalog_tool(
        "ignored",
        config=SimpleNamespace(),
        tool_id="tool.kb_retrieval.product-docs",
        payload={"input": {"query_text": "How do deployments work?", "top_k": 2}},
        actor_user_id=7,
    )

    assert captured == {
        "knowledge_base_id": "kb-product-docs",
        "payload": {
            "top_k": 2,
            "search_method": "semantic",
            "query_preprocessing": "none",
            "query_text": "How do deployments work?",
        },
    }
    assert result["execution"]["ok"] is True
    assert result["execution"]["result"]["results"][0]["text"] == "Relevant passage"


def test_execute_catalog_tool_rejects_unbound_knowledge_base(monkeypatch: pytest.MonkeyPatch):
    payload = _knowledge_base_retrieval_tool_payload()
    tool_row = {
        "entity_id": "tool.kb_retrieval.product-docs",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": payload,
    }
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    def _raise_unbound(*_args, **_kwargs):
        raise catalog_service.CatalogError("knowledge_base_not_bound", "Knowledge base is not bound.", status_code=409)

    monkeypatch.setattr(catalog_tool_backends, "find_active_bound_knowledge_base", _raise_unbound)

    with pytest.raises(catalog_service.CatalogError) as exc:
        catalog_service.execute_catalog_tool(
            "ignored",
            config=SimpleNamespace(),
            tool_id="tool.kb_retrieval.product-docs",
            payload={"input": {"query_text": "How do deployments work?"}},
            actor_user_id=7,
        )

    assert exc.value.code == "knowledge_base_not_bound"


def test_mcp_creation_options_use_backend_metadata_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        catalog_service,
        "list_catalog_tools",
        lambda _db: [
            {
                "id": "tool.kb_retrieval.product-docs",
                "spec": {
                    "name": "Product Docs Retrieval",
                    "execution_backend": "knowledge_base_retrieval",
                    "offline_compatible": True,
                },
            }
        ],
    )

    options = catalog_service.get_catalog_mcp_creation_options("ignored")

    assert options["tools"][0]["tool_id"] == "tool.kb_retrieval.product-docs"
    assert options["tools"][0]["metadata_defaults"]["category"] == "knowledge_retrieval"
    assert options["tools"][0]["metadata_defaults"]["data_access"] == "workspace"


def test_create_and_update_catalog_agent_use_registry_versions(monkeypatch: pytest.MonkeyPatch):
    entities: dict[str, dict] = {}

    def _find_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        return entities.get(f"{entity_type}:{entity_id}")

    def _create_registry_entity(_db: str, *, entity_id: str, entity_type: str, owner_user_id: int, visibility: str, status: str):
        row = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "owner_user_id": owner_user_id,
            "visibility": visibility,
            "status": status,
            "current_version": None,
            "current_spec": None,
            "published_at": None,
        }
        entities[f"{entity_type}:{entity_id}"] = row
        return row

    def _create_registry_version(_db: str, *, entity_id: str, version: str, spec_json: dict, set_current: bool, published: bool):
        row = entities[f"agent:{entity_id}"]
        row["current_version"] = version
        row["current_spec"] = spec_json
        row["published_at"] = "2026-01-01T00:00:00+00:00" if published else None
        return {"entity_id": entity_id, "version": version, "spec_json": spec_json}

    def _update_registry_entity(_db: str, *, entity_id: str, visibility: str | None = None, status: str | None = None):
        row = entities[f"agent:{entity_id}"]
        if visibility is not None:
            row["visibility"] = visibility
        if status is not None:
            row["status"] = status
        return row

    monkeypatch.setattr(catalog_service, "find_registry_entity", _find_registry_entity)
    monkeypatch.setattr(catalog_service, "create_registry_entity", _create_registry_entity)
    monkeypatch.setattr(catalog_service, "create_registry_version", _create_registry_version)
    monkeypatch.setattr(catalog_service, "update_registry_entity", _update_registry_entity)

    created = catalog_service.create_catalog_agent(
        "ignored",
        owner_user_id=3,
        payload={
            "id": "agent.alpha",
            "publish": False,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "runtime_prompts": {"retrieval_context": "Use retrieved context."},
            "default_model_ref": None,
            "tool_refs": [],
            "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        },
    )

    updated = catalog_service.update_catalog_agent(
        "ignored",
        agent_id="agent.alpha",
        payload={
            "publish": True,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "runtime_prompts": {"retrieval_context": "Use retrieved context and cite it."},
            "default_model_ref": "safe-small",
            "tool_refs": [],
            "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        },
    )

    assert created["current_version"] == "v1"
    assert created["spec"]["runtime_prompts"]["retrieval_context"] == "Use retrieved context."
    assert created["published"] is False
    assert updated["current_version"] == "v2"
    assert updated["spec"]["runtime_prompts"]["retrieval_context"] == "Use retrieved context and cite it."
    assert updated["published"] is True
    assert updated["status"] == "published"


def test_delete_catalog_agent_blocks_platform_agent_and_allows_owner(monkeypatch: pytest.MonkeyPatch):
    rows = {
        "agent:agent.knowledge_chat": {
            "entity_id": "agent.knowledge_chat",
            "entity_type": "agent",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "current_spec": {},
            "published_at": "2026-01-01T00:00:00+00:00",
        },
        "agent:agent.user": {
            "entity_id": "agent.user",
            "entity_type": "agent",
            "owner_user_id": 7,
            "visibility": "private",
            "status": "draft",
            "current_version": "v1",
            "current_spec": {},
            "published_at": None,
        },
    }
    deleted: list[str] = []

    def _find_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        return rows.get(f"{entity_type}:{entity_id}")

    def _delete_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        deleted.append(f"{entity_type}:{entity_id}")
        rows.pop(f"{entity_type}:{entity_id}", None)
        return True

    monkeypatch.setattr(catalog_service, "find_registry_entity", _find_registry_entity)
    monkeypatch.setattr(catalog_service, "delete_registry_entity", _delete_registry_entity)

    with pytest.raises(catalog_service.CatalogError) as exc_info:
        catalog_service.delete_catalog_agent(
            "ignored",
            agent_id="agent.knowledge_chat",
            actor_user_id=1,
            actor_role="superadmin",
        )

    assert exc_info.value.code == "platform_agent_delete_blocked"

    with pytest.raises(catalog_service.CatalogError) as forbidden_info:
        catalog_service.delete_catalog_agent(
            "ignored",
            agent_id="agent.user",
            actor_user_id=9,
            actor_role="user",
        )

    assert forbidden_info.value.code == "agent_delete_forbidden"

    catalog_service.delete_catalog_agent(
        "ignored",
        agent_id="agent.user",
        actor_user_id=7,
        actor_role="user",
    )

    assert deleted == ["agent:agent.user"]


def test_validate_catalog_agent_checks_model_and_tool_runtime_constraints(monkeypatch: pytest.MonkeyPatch):
    tool_rows = {
        "tool.web_search": {
            "entity_id": "tool.web_search",
            "entity_type": "tool",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "published_at": "2026-01-01T00:00:00+00:00",
            "current_spec": {
                "name": "Web search",
                "description": "desc",
                "transport": "mcp",
                "connection_profile_ref": "default",
                "tool_name": "web_search",
                "input_schema": {},
                "output_schema": {},
                "safety_policy": {},
                "offline_compatible": False,
            },
        },
        "tool.python_exec": {
            "entity_id": "tool.python_exec",
            "entity_type": "tool",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "published_at": "2026-01-01T00:00:00+00:00",
            "current_spec": {
                "name": "Python exec",
                "description": "desc",
                "transport": "sandbox_http",
                "connection_profile_ref": "default",
                "tool_name": "python_exec",
                "input_schema": {},
                "output_schema": {},
                "safety_policy": {},
                "offline_compatible": True,
            },
        },
    }

    monkeypatch.setattr(
        catalog_service,
        "find_registry_entity",
        lambda _db, *, entity_type, entity_id: {
            "entity_id": "agent.alpha",
            "entity_type": "agent",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "draft",
            "current_version": "v1",
            "published_at": None,
            "current_spec": {
                "name": "Agent Alpha",
                "description": "desc",
                "instructions": "be concise",
                "default_model_ref": "missing-model",
                "tool_refs": [entity_id] if entity_type == "tool" else ["tool.web_search", "tool.python_exec"],
                "runtime_constraints": {"internet_required": False, "sandbox_required": False},
            },
        }
        if entity_type == "agent"
        else tool_rows.get(entity_id),
    )
    monkeypatch.setattr(catalog_service, "find_model_definition", lambda _db, model_id: None)

    result = catalog_service.validate_catalog_agent("ignored", agent_id="agent.alpha")

    assert result["validation"]["valid"] is False
    assert "Model 'missing-model' does not exist." in result["validation"]["errors"]
    assert "Agent references online-only tools but runtime_constraints.internet_required is false." in result["validation"]["errors"]
    assert "Agent references sandbox tools but runtime_constraints.sandbox_required is false." in result["validation"]["errors"]
    assert result["validation"]["derived_runtime_requirements"]["internet_required"] is True
    assert result["validation"]["derived_runtime_requirements"]["sandbox_required"] is True


def test_preview_catalog_agent_prompt_uses_normalized_runtime_prompts(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        catalog_service,
        "find_registry_entity",
        lambda _db, *, entity_type, entity_id: {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "owner_user_id": 1,
            "visibility": "private",
            "status": "draft",
            "current_version": "v1",
            "published_at": None,
            "current_spec": {
                "name": "Agent Alpha",
                "description": "desc",
                "instructions": "Answer from catalog instructions.",
                "default_model_ref": None,
                "tool_refs": [],
                "runtime_constraints": {"internet_required": False, "sandbox_required": False},
            },
        },
    )

    stored_preview = catalog_service.preview_catalog_agent_prompt("ignored", agent_id="agent.alpha")
    draft_preview = catalog_service.preview_catalog_agent_prompt_payload(
        {
            "instructions": "Draft instructions.",
            "runtime_prompts": {"retrieval_context": "Draft retrieval instructions."},
        }
    )

    assert "Answer from catalog instructions." in stored_preview["prompt_preview"]["text"]
    assert "Use the following retrieved context" in stored_preview["prompt_preview"]["text"]
    assert draft_preview["prompt_preview"]["messages"][0]["content"] == "Draft instructions."
    assert "Draft retrieval instructions." in draft_preview["prompt_preview"]["messages"][1]["content"]


def test_validate_catalog_tool_requires_active_runtime_and_discovers_mcp_tools(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.web_search",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "draft",
        "current_version": "v1",
        "published_at": None,
        "current_spec": {
            "name": "Web search",
            "description": "desc",
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
    }
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    class HealthyMcpAdapter:
        def health(self):
            return {"reachable": True, "status_code": 200}

        def list_tools(self):
            return {"tools": [{"tool_name": "web_search"}]}, 200

    result_ok = None
    monkeypatch.setattr(catalog_tool_backends, "resolve_mcp_runtime_adapter", lambda _db, config: HealthyMcpAdapter())
    result_ok = catalog_service.validate_catalog_tool("ignored", config=SimpleNamespace(), tool_id="tool.web_search")

    assert result_ok["validation"]["valid"] is True
    assert result_ok["validation"]["runtime_checks"]["tool_discovered"] is True

    monkeypatch.setattr(
        catalog_tool_backends,
        "resolve_mcp_runtime_adapter",
        lambda _db, config: (_ for _ in ()).throw(
            PlatformControlPlaneError("missing_active_binding", "Active platform runtime is missing capability 'mcp_runtime'", status_code=404)
        ),
    )
    result_missing = catalog_service.validate_catalog_tool("ignored", config=SimpleNamespace(), tool_id="tool.web_search")

    assert result_missing["validation"]["valid"] is False
    assert "Active platform runtime is missing capability 'mcp_runtime'" in result_missing["validation"]["errors"]


def test_execute_catalog_tool_invokes_mcp_runtime(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.web_search",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": {
            "name": "Web search",
            "description": "desc",
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
    }
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    captured: dict[str, object] = {}

    class HealthyMcpAdapter:
        def invoke(self, *, tool_name: str, arguments: dict[str, object], request_metadata: dict[str, object]):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            captured["request_metadata"] = request_metadata
            return {"results": [{"title": "Example"}]}, 200

    monkeypatch.setattr(catalog_tool_backends, "resolve_mcp_runtime_adapter", lambda _db, config: HealthyMcpAdapter())

    result = catalog_service.execute_catalog_tool(
        "ignored",
        config=SimpleNamespace(),
        tool_id="tool.web_search",
        payload={"input": {"query": "OpenAI", "top_k": 3}},
        actor_user_id=7,
    )

    assert captured == {
        "tool_name": "web_search",
        "arguments": {"query": "OpenAI", "top_k": 3},
        "request_metadata": {"actor_user_id": 7},
    }
    assert result["execution"]["ok"] is True
    assert result["execution"]["result"]["results"][0]["title"] == "Example"


def test_execute_catalog_tool_invokes_sandbox_runtime(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.python_exec",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": {
            "name": "Python exec",
            "description": "desc",
            "transport": "sandbox_http",
            "connection_profile_ref": "default",
            "tool_name": "python_exec",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {"timeout_seconds": 5, "network_access": False},
            "offline_compatible": True,
        },
    }
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    captured: dict[str, object] = {}

    class HealthySandboxAdapter:
        def execute(self, *, code: str, language: str, input_payload, timeout_seconds: int, policy: dict[str, object]):
            captured["code"] = code
            captured["language"] = language
            captured["input_payload"] = input_payload
            captured["timeout_seconds"] = timeout_seconds
            captured["policy"] = policy
            return {"stdout": "3\n", "stderr": "", "result": 3}, 200

    monkeypatch.setattr(catalog_tool_backends, "resolve_sandbox_execution_adapter", lambda _db, config: HealthySandboxAdapter())

    result = catalog_service.execute_catalog_tool(
        "ignored",
        config=SimpleNamespace(),
        tool_id="tool.python_exec",
        payload={"input": {"code": "print(1 + 2)", "input": {"value": 2}}},
        actor_user_id=7,
    )

    assert captured == {
        "code": "print(1 + 2)",
        "language": "python",
        "input_payload": {"value": 2},
        "timeout_seconds": 5,
        "policy": {"timeout_seconds": 5, "network_access": False},
    }
    assert result["execution"]["ok"] is True
    assert result["execution"]["result"]["result"] == 3
