from __future__ import annotations

from typing import Any


def _m():
    import app.app as backend_app_module

    return backend_app_module


def coerce_chat_messages(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        if not content:
            continue
        normalized.append(
            {
                "role": role,
                "content": [{"type": "text", "text": content}],
            }
        )
    return normalized


def extract_output_text(llm_response: dict[str, Any]) -> str:
    output = llm_response.get("output")
    if not isinstance(output, list) or len(output) == 0:
        return ""

    first = output[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, list) or len(content) == 0:
        return ""

    text_parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and str(part.get("type", "")).lower() == "text":
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def chat_completion_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[dict[str, Any] | None, int]:
    m = _m()
    effective_models = m._effective_models_for_current_user(org_id=org_id, group_id=group_id)
    allowed_model_ids = {str(model.get("model_id", "")) for model in effective_models}
    if requested_model_id not in allowed_model_ids:
        return {"error": "model_forbidden", "message": "Requested model is not allowed"}, 403

    llm_url = m.os.getenv("LLM_URL", "http://llm:8000").rstrip("/")
    upstream_payload: dict[str, Any] = {
        "model": requested_model_id,
        "input": messages,
    }
    if max_tokens is not None:
        upstream_payload["max_tokens"] = max_tokens
    if temperature is not None:
        upstream_payload["temperature"] = temperature

    return m._http_json_request(f"{llm_url}/v1/chat/completions", upstream_payload)
