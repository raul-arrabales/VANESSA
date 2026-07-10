from __future__ import annotations

from typing import Any

LLM_DEBUG_STATUS_KIND = "llm_call"
LLM_DEBUG_DETAILS_KEY = "llm_debug"
MAX_DEBUG_TOOLS_CHARS = 4_000
MAX_DEBUG_TOOL_CALL_CHARS = 4_000
MAX_DEBUG_PARSED_JSON_CHARS = 4_000
MAX_DEBUG_PREVIEW_CHARS = 600


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            part_type = str(part.get("type") or "").strip()
            if part_type.lower() == "text":
                text = str(part.get("text") or "")
                if text:
                    text_parts.append(text)
            elif part_type:
                text_parts.append(f"[{part_type}]")
        return "\n".join(text_parts)
    return str(content or "")


def llm_debug_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip() or "message"
        normalized.append({"role": role, "text": _message_text(message.get("content"))})
    return normalized


def compact_debug_payload(value: Any, *, limit: int = MAX_DEBUG_PREVIEW_CHARS) -> Any:
    if isinstance(value, dict):
        return {str(key): compact_debug_payload(item, limit=limit) for key, item in value.items()}
    if isinstance(value, list):
        return [compact_debug_payload(item, limit=limit) for item in value]
    if isinstance(value, str):
        text = value
        if len(text) <= limit:
            return text
        return f"{text[: max(limit - 1, 0)].rstrip()}..."
    return value


def build_llm_debug_payload(
    *,
    call_id: str,
    call_label: str,
    messages: list[dict[str, Any]],
    requested_model: str | None,
    provider_telemetry: dict[str, Any] | None = None,
    agent_id: str | None = None,
    assistant_ref: str | None = None,
    raw_response_text: str | None = None,
    tools: Any = None,
    tool_calls: Any = None,
    parsed_json: Any = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    telemetry = provider_telemetry if isinstance(provider_telemetry, dict) else {}
    payload: dict[str, Any] = {
        "call_id": call_id,
        "call_label": call_label,
        "requested_model": requested_model,
        "provider_slug": telemetry.get("provider_slug"),
        "provider_key": telemetry.get("provider_key"),
        "deployment_profile_slug": telemetry.get("deployment_profile_slug"),
        "messages": llm_debug_messages(messages),
    }
    if agent_id:
        payload["agent_id"] = agent_id
    if assistant_ref:
        payload["assistant_ref"] = assistant_ref
    if tools is not None:
        payload["tools"] = compact_debug_payload(tools, limit=MAX_DEBUG_TOOLS_CHARS)
    if raw_response_text is not None:
        payload["raw_response_text"] = raw_response_text
    if tool_calls is not None:
        payload["tool_calls"] = compact_debug_payload(tool_calls, limit=MAX_DEBUG_TOOL_CALL_CHARS)
    if parsed_json is not None:
        payload["parsed_json"] = compact_debug_payload(parsed_json, limit=MAX_DEBUG_PARSED_JSON_CHARS)
    if status_code is not None:
        payload["status_code"] = status_code
    return payload


def llm_debug_details(payload: dict[str, Any]) -> dict[str, Any]:
    return {LLM_DEBUG_DETAILS_KEY: payload}
