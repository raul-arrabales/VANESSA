from __future__ import annotations

from typing import Any

from .base import McpToolRuntimeClient, SandboxToolRuntimeClient, ToolRuntimeClientError
from .resolution import binding_timeout_seconds
from .transport import JsonRequestFn, request_json_or_raise


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
        payload, status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=ToolRuntimeClientError,
            binding=self.mcp_binding,
            url=self._invoke_url(),
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
