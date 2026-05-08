from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import cloud_traffic  # noqa: E402
from agent_engine.app.services.runtime_clients.tool_runtime import HttpMcpToolRuntimeClient  # noqa: E402


def test_cloud_traffic_helper_reports_cloud_binding_and_skips_local(monkeypatch):
    seen_events: list[dict[str, object]] = []
    monkeypatch.setattr(cloud_traffic, "report_cloud_traffic_event", lambda event: seen_events.append(dict(event)))

    cloud_traffic.report_cloud_traffic_for_binding(
        {"provider_origin": "local", "provider_key": "vllm_local", "slug": "local"},
        direction="egress",
        phase="request_sent",
        capability="llm_inference",
        operation="llm.chat_completion",
        endpoint_url="http://llm:8000/v1/chat/completions",
    )
    cloud_traffic.report_cloud_traffic_for_binding(
        {"provider_origin": "cloud", "provider_key": "openai_compatible_cloud_llm", "slug": "openai"},
        direction="egress",
        phase="request_sent",
        capability="llm_inference",
        operation="llm.chat_completion",
        endpoint_url="https://api.openai.com/v1/chat/completions",
    )

    assert len(seen_events) == 1
    assert seen_events[0]["provider_origin"] == "cloud"
    assert seen_events[0]["endpoint_host"] == "api.openai.com"


def test_web_search_tool_dispatch_reports_external_traffic(monkeypatch):
    from agent_engine.app.services.runtime_clients import tool_runtime

    reports: list[dict[str, object]] = []

    def _report(_binding, **kwargs):
        reports.append(dict(kwargs))

    def _request_json(**_kwargs):
        return {"result": {"query": "hello", "results": []}}, 200

    monkeypatch.setattr(tool_runtime, "report_cloud_traffic_for_binding", _report)
    client = HttpMcpToolRuntimeClient(
        deployment_profile={"slug": "online"},
        mcp_binding={
            "slug": "mcp-gateway-local",
            "provider_key": "mcp_gateway_local",
            "provider_origin": "local",
            "endpoint_url": "http://mcp_gateway:8080",
            "config": {"invoke_path": "/v1/tools/invoke"},
        },
        request_json=lambda *args, **kwargs: _request_json(**kwargs),
    )

    client.invoke(tool_name="web_search", arguments={"query": "hello"}, request_metadata={"tool_ref": "tool.web_search"})

    assert [report["direction"] for report in reports] == ["egress", "ingress"]
    assert all(report["force_external"] is True for report in reports)
    assert all(report["operation"] == "tool.web_search" for report in reports)
