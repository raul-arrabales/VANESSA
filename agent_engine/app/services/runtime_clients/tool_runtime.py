from __future__ import annotations

from time import monotonic
from typing import Any

from .base import ImageAnalysisRuntimeClient, ImageAnalysisRuntimeClientError, McpToolRuntimeClient, SandboxToolRuntimeClient, ToolRuntimeClientError
from .image_analysis_tasks import IMAGE_ANALYSIS_DEFAULTS_BY_TASK
from .resolution import binding_timeout_seconds
from .transport import JsonRequestFn, request_json_or_raise
from ..cloud_traffic import report_cloud_traffic_for_binding


def tool_unavailable_code(status_code: int) -> str:
    return "tool_runtime_timeout" if status_code == 504 else "tool_runtime_unreachable"


def tool_request_failed_code(status_code: int) -> str:
    if status_code == 504:
        return "tool_runtime_timeout"
    if status_code >= 502:
        return "tool_runtime_upstream_unavailable"
    return "tool_runtime_request_failed"


class HttpMcpToolRuntimeClient(McpToolRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        mcp_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, mcp_binding=mcp_binding)
        self.request_json = request_json

    def invoke(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        request_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        invoke_url = self._invoke_url()
        is_external_web_search = tool_name.strip().lower() == "web_search"
        started_at = monotonic()
        report_cloud_traffic_for_binding(
            self.mcp_binding,
            direction="egress",
            phase="request_sent",
            capability="mcp_runtime",
            operation=f"tool.{tool_name.strip().lower() or 'unknown'}",
            endpoint_url="external-web" if is_external_web_search else invoke_url,
            force_external=is_external_web_search,
        )
        try:
            payload, status_code = request_json_or_raise(
                request_json=self.request_json,
                error_cls=ToolRuntimeClientError,
                binding=self.mcp_binding,
                url=invoke_url,
                method="POST",
                payload={
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "request_metadata": request_metadata,
                },
                timeout_seconds=binding_timeout_seconds(self.mcp_binding),
                unavailable_code=tool_unavailable_code,
                unavailable_message="Tool runtime unavailable",
                request_failed_code=tool_request_failed_code,
                request_failed_message="Tool runtime request failed",
            )
        except ToolRuntimeClientError as exc:
            report_cloud_traffic_for_binding(
                self.mcp_binding,
                direction="ingress",
                phase="response_failed",
                capability="mcp_runtime",
                operation=f"tool.{tool_name.strip().lower() or 'unknown'}",
                endpoint_url="external-web" if is_external_web_search else invoke_url,
                status_code=exc.status_code,
                duration_ms=int((monotonic() - started_at) * 1000),
                force_external=is_external_web_search,
            )
            raise
        report_cloud_traffic_for_binding(
            self.mcp_binding,
            direction="ingress",
            phase="response_received",
            capability="mcp_runtime",
            operation=f"tool.{tool_name.strip().lower() or 'unknown'}",
            endpoint_url="external-web" if is_external_web_search else invoke_url,
            status_code=status_code,
            duration_ms=int((monotonic() - started_at) * 1000),
            force_external=is_external_web_search,
        )
        return {
            "status_code": status_code,
            "tool_name": tool_name,
            "result": payload.get("result"),
            "error": payload.get("error"),
        }

    def _invoke_url(self) -> str:
        config = self.mcp_binding.get("config") if isinstance(self.mcp_binding.get("config"), dict) else {}
        invoke_path = str(config.get("invoke_path", "/v1/tools/invoke")).strip() or "/v1/tools/invoke"
        endpoint_url = str(self.mcp_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + invoke_path


class HttpSandboxToolRuntimeClient(SandboxToolRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        sandbox_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, sandbox_binding=sandbox_binding)
        self.request_json = request_json

    def execute_python(
        self,
        *,
        code: str,
        input_payload: Any,
        timeout_seconds: int,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        payload, status_code = self.request_json(
            self._execute_url(),
            method="POST",
            payload={
                "language": "python",
                "code": code,
                "input": input_payload,
                "timeout_seconds": timeout_seconds,
                "policy": policy,
            },
            timeout_seconds=binding_timeout_seconds(self.sandbox_binding),
        )
        if payload is None:
            raise ToolRuntimeClientError(
                code=tool_unavailable_code(status_code),
                message="Tool runtime unavailable",
                status_code=status_code,
                details={"provider_slug": self.sandbox_binding.get("slug"), "status_code": status_code},
            )
        if status_code == 504:
            raise ToolRuntimeClientError(
                code="tool_runtime_timeout",
                message="Tool runtime request timed out",
                status_code=status_code,
                details={"provider_slug": self.sandbox_binding.get("slug"), "status_code": status_code},
            )
        if status_code >= 502:
            raise ToolRuntimeClientError(
                code="tool_runtime_upstream_unavailable",
                message="Tool runtime request failed",
                status_code=status_code,
                details={
                    "provider_slug": self.sandbox_binding.get("slug"),
                    "status_code": status_code,
                    "upstream": payload,
                },
            )
        return {
            "status_code": status_code,
            "stdout": payload.get("stdout", ""),
            "stderr": payload.get("stderr", ""),
            "result": payload.get("result"),
            "error": payload.get("error"),
        }

    def _execute_url(self) -> str:
        config = self.sandbox_binding.get("config") if isinstance(self.sandbox_binding.get("config"), dict) else {}
        execute_path = str(config.get("execute_path", "/v1/execute")).strip() or "/v1/execute"
        endpoint_url = str(self.sandbox_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + execute_path


class HttpImageAnalysisRuntimeClient(ImageAnalysisRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        image_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, image_binding=image_binding)
        self.request_json = request_json

    def analyze(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        resource_policy = self.image_binding.get("resource_policy") if isinstance(self.image_binding.get("resource_policy"), dict) else {}
        task_defaults = resource_policy.get("task_defaults") if isinstance(resource_policy.get("task_defaults"), dict) else {}
        tasks = payload.get("tasks") if isinstance(payload.get("tasks"), list) else []
        missing_defaults = [
            default_key
            for task in [str(item).strip().lower() for item in tasks if str(item).strip()]
            for default_key in IMAGE_ANALYSIS_DEFAULTS_BY_TASK.get(task, ())
            if not str(task_defaults.get(default_key) or "").strip()
        ]
        if missing_defaults:
            raise ImageAnalysisRuntimeClientError(
                code="missing_image_analysis_task_defaults",
                message="platform_runtime image_analysis binding is missing task defaults for requested tasks",
                status_code=409,
                details={"missing_task_defaults": sorted(set(missing_defaults)), "tasks": tasks},
            )
        analysis_payload = {
            **payload,
            "runtime": {
                "resources": list(self.image_binding.get("resources") or []),
                "task_defaults": dict(task_defaults),
            },
        }
        response_payload, status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=ImageAnalysisRuntimeClientError,
            binding=self.image_binding,
            url=self._analyze_url(),
            method="POST",
            payload=analysis_payload,
            timeout_seconds=binding_timeout_seconds(self.image_binding),
            unavailable_code=tool_unavailable_code,
            unavailable_message="Image analysis runtime unavailable",
            request_failed_code=tool_request_failed_code,
            request_failed_message="Image analysis runtime request failed",
        )
        return {"status_code": status_code, "result": response_payload}

    def _analyze_url(self) -> str:
        config = self.image_binding.get("config") if isinstance(self.image_binding.get("config"), dict) else {}
        analyze_path = str(config.get("analyze_path", "/v1/analyze")).strip() or "/v1/analyze"
        endpoint_url = str(self.image_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + analyze_path
