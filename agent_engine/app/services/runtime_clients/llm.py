from __future__ import annotations

from json import dumps
from typing import Any

from .base import LlmRuntimeClient, LlmRuntimeClientError
from .resolution import binding_timeout_seconds, resolve_effective_model
from .transport import JsonRequestFn, request_json_or_raise


def llm_request_failed_code(status_code: int) -> str:
    if status_code == 504:
        return "runtime_timeout"
    if status_code >= 502:
        return "runtime_upstream_unavailable"
    return "runtime_request_failed"


class OpenAICompatibleLlmRuntimeClient(LlmRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        llm_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, llm_binding=llm_binding)
        self.request_json = request_json

    def chat_completion(
        self,
        *,
        requested_model: str | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        selected_model_id, runtime_model_id = resolve_effective_model(
            requested_model,
            self.llm_binding,
            request_json=self.request_json,
        )
        payload = build_request_payload(self.llm_binding, runtime_model_id, messages, tools=tools)
        response_payload, status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=LlmRuntimeClientError,
            binding=self.llm_binding,
            url=self._chat_url(),
            method="POST",
            payload=payload,
            timeout_seconds=binding_timeout_seconds(self.llm_binding),
            unavailable_code="runtime_unreachable",
            unavailable_message="LLM runtime unavailable",
            request_failed_code=llm_request_failed_code,
            request_failed_message="LLM runtime request failed",
        )
        return {
            "output_text": extract_output_text(response_payload),
            "tool_calls": extract_tool_calls(response_payload),
            "status_code": status_code,
            "requested_model": selected_model_id,
        }

    def _chat_url(self) -> str:
        config = self.llm_binding.get("config") if isinstance(self.llm_binding.get("config"), dict) else {}
        chat_path = str(config.get("chat_completion_path", "/v1/chat/completions")).strip() or "/v1/chat/completions"
        endpoint_url = str(self.llm_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + chat_path


def build_request_payload(
    llm_binding: dict[str, Any],
    model: str,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = llm_binding.get("config") if isinstance(llm_binding.get("config"), dict) else {}
    request_format = str(config.get("request_format", "responses_api")).strip().lower() or "responses_api"
    if request_format == "openai_chat":
        payload: dict[str, Any] = {
            "model": model,
            "messages": coerce_openai_chat_messages(messages),
        }
        if tools:
            payload["tools"] = tools
        return payload
    payload = {
        "model": model,
        "input": messages,
    }
    if tools:
        payload["tools"] = tools
    return payload


def coerce_openai_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        if not role:
            continue
        tool_calls = message.get("tool_calls")
        if role == "assistant" and isinstance(tool_calls, list) and tool_calls:
            normalized.append(
                {
                    "role": "assistant",
                    "content": coerce_message_text(message.get("content")),
                    "tool_calls": [
                        {
                            "id": str(item.get("id", "")).strip(),
                            "type": "function",
                            "function": {
                                "name": str((item.get("function") or {}).get("name", "")).strip(),
                                "arguments": str((item.get("function") or {}).get("arguments", "")),
                            },
                        }
                        for item in tool_calls
                        if isinstance(item, dict) and isinstance(item.get("function"), dict)
                    ],
                }
            )
            continue
        if role == "tool":
            tool_call_id = str(message.get("tool_call_id", "")).strip()
            if tool_call_id:
                normalized.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": coerce_message_text(message.get("content")),
                    }
                )
                continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            normalized.append({"role": role, "content": content.strip()})
            continue
        if not isinstance(content, list):
            continue
        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
        if text_parts:
            normalized.append({"role": role, "content": "\n".join(text_parts)})
    return normalized


def coerce_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if str(part.get("type", "")).strip().lower() != "text":
            continue
        text = str(part.get("text", "")).strip()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def extract_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if str(part.get("type", "")).strip().lower() != "text":
                    continue
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    return ""


def extract_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = payload.get("output")
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, dict):
            normalized = normalize_tool_calls(first.get("tool_calls"))
            if normalized:
                return normalized
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                normalized = normalize_tool_calls(message.get("tool_calls"))
                if normalized:
                    return normalized
    return []


def normalize_tool_calls(raw_tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_tool_calls, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_tool_calls:
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        tool_id = str(item.get("id", "")).strip()
        function_name = str(function.get("name", "")).strip()
        if not tool_id or not function_name:
            continue
        normalized.append(
            {
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": function_name,
                    "arguments": str(function.get("arguments", "")),
                },
            }
        )
    return normalized


def graphql_string(value: str) -> str:
    return dumps(value)
