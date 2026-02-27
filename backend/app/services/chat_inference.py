from __future__ import annotations

import os
from json import dumps, loads
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import g

from ..config import get_auth_config
from ..repositories.model_access import list_effective_allowed_models

_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5


def http_json_request(url: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    req = Request(
        url,
        data=dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            status_code = int(response.status)
            body = response.read().decode("utf-8")
            return (loads(body) if body else {}), status_code
    except HTTPError as error:
        body = error.read().decode("utf-8")
        parsed = loads(body) if body else {"error": "upstream_error"}
        return parsed, int(error.code)
    except URLError:
        return None, 502


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
    effective_models = list_effective_allowed_models(
        get_auth_config().database_url,
        user_id=int(g.current_user["id"]),
        org_id=org_id,
        group_id=group_id,
    )
    allowed_model_ids = {str(model.get("model_id", "")) for model in effective_models}
    if requested_model_id not in allowed_model_ids:
        return {"error": "model_forbidden", "message": "Requested model is not allowed"}, 403

    llm_url = os.getenv("LLM_URL", "http://llm:8000").rstrip("/")
    upstream_payload: dict[str, Any] = {
        "model": requested_model_id,
        "input": messages,
    }
    if max_tokens is not None:
        upstream_payload["max_tokens"] = max_tokens
    if temperature is not None:
        upstream_payload["temperature"] = temperature

    return http_json_request(f"{llm_url}/v1/chat/completions", upstream_payload)
