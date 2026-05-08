from __future__ import annotations

from collections.abc import Iterator
from json import dumps
from time import monotonic
from typing import Any

from .base import LlmRuntimeClient, LlmRuntimeClientError
from .resolution import binding_timeout_seconds, resolve_effective_model
from .secrets import openai_compatible_headers
from .transport import JsonRequestFn, StreamRequestError, stream_sse_request, request_json_or_raise
from ..cloud_traffic import report_cloud_traffic_for_binding

_REQUEST_OPTION_KEYS = {
    "service_tier",
    "prompt_cache_key",
    "prompt_cache_retention",
}


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
        add_openai_compatible_request_options(payload, self.llm_binding, stream=False)
        chat_url = self._chat_url()
        started_at = monotonic()
        report_cloud_traffic_for_binding(
            self.llm_binding,
            direction="egress",
            phase="request_sent",
            capability="llm_inference",
            operation="llm.chat_completion",
            endpoint_url=chat_url,
        )
        try:
            response_payload, status_code = request_json_or_raise(
                request_json=self.request_json,
                error_cls=LlmRuntimeClientError,
                binding=self.llm_binding,
                url=chat_url,
                method="POST",
                payload=payload,
                headers=openai_compatible_headers(self.llm_binding, error_cls=LlmRuntimeClientError),
                timeout_seconds=binding_timeout_seconds(self.llm_binding),
                unavailable_code="runtime_unreachable",
                unavailable_message="LLM runtime unavailable",
                request_failed_code=llm_request_failed_code,
                request_failed_message="LLM runtime request failed",
            )
        except LlmRuntimeClientError as exc:
            report_cloud_traffic_for_binding(
                self.llm_binding,
                direction="ingress",
                phase="response_failed",
                capability="llm_inference",
                operation="llm.chat_completion",
                endpoint_url=chat_url,
                status_code=exc.status_code,
                duration_ms=int((monotonic() - started_at) * 1000),
            )
            raise
        report_cloud_traffic_for_binding(
            self.llm_binding,
            direction="ingress",
            phase="response_received",
            capability="llm_inference",
            operation="llm.chat_completion",
            endpoint_url=chat_url,
            status_code=status_code,
            duration_ms=int((monotonic() - started_at) * 1000),
        )
        return {
            "output_text": extract_output_text(response_payload),
            "tool_calls": extract_tool_calls(response_payload),
            "status_code": status_code,
            "requested_model": selected_model_id,
        }

    def chat_completion_stream(
        self,
        *,
        requested_model: str | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        selected_model_id, runtime_model_id = resolve_effective_model(
            requested_model,
            self.llm_binding,
            request_json=self.request_json,
        )
        payload = build_request_payload(self.llm_binding, runtime_model_id, messages, tools=tools)
        payload["stream"] = True
        add_openai_compatible_request_options(payload, self.llm_binding, stream=True)
        request_format = self._request_format()
        chat_url = self._chat_url()
        raw_events = _cloud_traced_stream_request(
            self.llm_binding,
            chat_url,
            method="POST",
            payload=payload,
            headers=openai_compatible_headers(self.llm_binding, error_cls=LlmRuntimeClientError),
            timeout_seconds=binding_timeout_seconds(self.llm_binding),
        )
        try:
            if request_format == "openai_chat":
                yield from _iter_openai_chat_stream_events(raw_events, requested_model=selected_model_id)
                return
            yield from _iter_vanessa_chat_stream_events(raw_events, requested_model=selected_model_id)
        except StreamRequestError as exc:
            yield {
                "type": "error",
                "payload": exc.payload or {"error": "llm_stream_unreachable", "message": str(exc)},
                "status_code": exc.status_code,
            }

    def _chat_url(self) -> str:
        config = self.llm_binding.get("config") if isinstance(self.llm_binding.get("config"), dict) else {}
        chat_path = str(config.get("chat_completion_path", "/v1/chat/completions")).strip() or "/v1/chat/completions"
        endpoint_url = str(self.llm_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + chat_path

    def _request_format(self) -> str:
        config = self.llm_binding.get("config") if isinstance(self.llm_binding.get("config"), dict) else {}
        return str(config.get("request_format", "responses_api")).strip().lower() or "responses_api"


def _cloud_traced_stream_request(
    binding: dict[str, Any],
    url: str,
    *,
    method: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> Iterator[tuple[str, dict[str, Any]]]:
    started_at = monotonic()
    report_cloud_traffic_for_binding(
        binding,
        direction="egress",
        phase="request_sent",
        capability="llm_inference",
        operation="llm.chat_completion_stream",
        endpoint_url=url,
    )
    ingress_emitted = False
    try:
        for event_name, event_payload in stream_sse_request(
            url,
            method=method,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        ):
            if not ingress_emitted and event_name == "transport":
                ingress_emitted = True
                report_cloud_traffic_for_binding(
                    binding,
                    direction="ingress",
                    phase="first_stream_setup",
                    capability="llm_inference",
                    operation="llm.chat_completion_stream",
                    endpoint_url=url,
                    status_code=_safe_int(event_payload.get("status_code")),
                    duration_ms=_safe_int(event_payload.get("duration_ms")) or int((monotonic() - started_at) * 1000),
                )
            yield event_name, event_payload
    except StreamRequestError as exc:
        if not ingress_emitted:
            report_cloud_traffic_for_binding(
                binding,
                direction="ingress",
                phase="first_stream_setup_failed",
                capability="llm_inference",
                operation="llm.chat_completion_stream",
                endpoint_url=url,
                status_code=exc.status_code,
                duration_ms=int((monotonic() - started_at) * 1000),
            )
        raise


def _safe_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def add_openai_compatible_request_options(payload: dict[str, Any], llm_binding: dict[str, Any], *, stream: bool) -> None:
    config = llm_binding.get("config") if isinstance(llm_binding.get("config"), dict) else {}
    request_format = str(config.get("request_format", "responses_api")).strip().lower() or "responses_api"
    options = config.get("request_options") if isinstance(config.get("request_options"), dict) else {}
    merged_options = {**{key: config.get(key) for key in _REQUEST_OPTION_KEYS | {"reasoning_effort"}}, **options}
    for key in _REQUEST_OPTION_KEYS:
        value = merged_options.get(key)
        if value is not None and value != "":
            payload[key] = value

    reasoning_effort = merged_options.get("reasoning_effort")
    if reasoning_effort is not None and reasoning_effort != "":
        if request_format == "openai_chat":
            payload["reasoning_effort"] = reasoning_effort
        else:
            existing_reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), dict) else {}
            payload["reasoning"] = {**existing_reasoning, "effort": reasoning_effort}

    stream_options = config.get("stream_options") if isinstance(config.get("stream_options"), dict) else None
    if stream and stream_options:
        payload["stream_options"] = dict(stream_options)


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


def _iter_vanessa_chat_stream_events(
    raw_events: Iterator[tuple[str, dict[str, Any]]],
    *,
    requested_model: str,
) -> Iterator[dict[str, Any]]:
    text_parts: list[str] = []
    for event_name, event_payload in raw_events:
        normalized_event_name = event_name.strip().lower()
        if normalized_event_name == "transport":
            yield {
                "type": "transport",
                **event_payload,
            }
            continue
        if normalized_event_name == "delta":
            text = str(event_payload.get("text", ""))
            if text:
                text_parts.append(text)
                yield {"type": "delta", "text": text}
            continue
        if normalized_event_name == "complete":
            response_payload = event_payload.get("response")
            normalized_response = (
                normalize_stream_complete_response(response_payload, text_parts)
                if isinstance(response_payload, dict)
                else normalize_stream_complete_response(None, text_parts)
            )
            yield {
                "type": "complete",
                "response": normalized_response,
                "status_code": 200,
                "requested_model": requested_model,
            }
            return
        if normalized_event_name == "error":
            yield {
                "type": "error",
                "payload": event_payload,
                "status_code": int(event_payload.get("status_code", 502) or 502),
            }
            return


def _iter_openai_chat_stream_events(
    raw_events: Iterator[tuple[str, dict[str, Any]]],
    *,
    requested_model: str,
) -> Iterator[dict[str, Any]]:
    text_parts: list[str] = []
    usage_payload: dict[str, Any] | None = None
    for event_name, event_payload in raw_events:
        normalized_event_name = event_name.strip().lower()
        if normalized_event_name == "transport":
            yield {"type": "transport", **event_payload}
            continue
        if normalized_event_name != "message":
            for normalized_event in _iter_vanessa_chat_stream_events(iter([(event_name, event_payload)]), requested_model=requested_model):
                yield normalized_event
                if str(normalized_event.get("type") or "").strip().lower() in {"complete", "error"}:
                    return
            continue
        if str(event_payload.get("raw") or "").strip() == "[DONE]":
            yield _openai_chat_complete_event(text_parts, requested_model=requested_model, usage=usage_payload)
            return
        if isinstance(event_payload.get("usage"), dict):
            usage_payload = dict(event_payload["usage"])
        error_payload = event_payload.get("error")
        if isinstance(error_payload, dict):
            yield {
                "type": "error",
                "payload": error_payload,
                "status_code": int(event_payload.get("status_code", 502) or 502),
            }
            return
        choice = _first_openai_stream_choice(event_payload)
        if choice is None:
            continue
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                text_parts.append(content)
                yield {"type": "delta", "text": content}
                continue
        if str(choice.get("finish_reason") or "").strip():
            yield _openai_chat_complete_event(text_parts, requested_model=requested_model, usage=usage_payload)
            return


def _first_openai_stream_choice(event_payload: dict[str, Any]) -> dict[str, Any] | None:
    choices = event_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    return first if isinstance(first, dict) else None


def _openai_chat_complete_event(
    text_parts: list[str],
    *,
    requested_model: str,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = normalize_stream_complete_response(None, text_parts)
    if usage:
        response["usage"] = usage
    return {
        "type": "complete",
        "response": response,
        "status_code": 200,
        "requested_model": requested_model,
    }


def normalize_stream_complete_response(response_payload: dict[str, Any] | None, text_parts: list[str]) -> dict[str, Any]:
    if isinstance(response_payload, dict):
        return response_payload
    return {
        "output": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "".join(text_parts),
                    }
                ],
            }
        ]
    }


def graphql_string(value: str) -> str:
    return dumps(value)
