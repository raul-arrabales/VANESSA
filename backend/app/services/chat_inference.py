from __future__ import annotations

from json import dumps, loads
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import g

from ..config import get_auth_config
from ..repositories.model_management import get_model_by_id
from .model_resolution import resolve_model_for_inference

_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5
_LOCAL_LLM_MODEL_ID = "local-vllm-default"


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


def _is_model_not_found_error(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("code", "")).strip().lower() == "model_not_found"
    return str(payload.get("error", "")).strip().lower() == "model_not_found"


def _can_use_local_llm_fallback(requested_model_id: str) -> bool:
    model = get_model_by_id(get_auth_config().database_url, requested_model_id)
    if model is None:
        return False
    backend_kind = str(model.get("backend_kind", "")).strip().lower()
    availability = str(model.get("availability", "")).strip().lower()
    return backend_kind == "local" or availability == "offline_ready"


def chat_completion_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[dict[str, Any] | None, int]:
    _ = org_id
    _ = group_id
    resolved_model_id, error_payload, status_code = resolve_model_for_inference(
        get_auth_config().database_url,
        user_id=int(g.current_user["id"]),
        requested_model_id=requested_model_id,
    )
    if error_payload is not None:
        return error_payload, status_code

    llm_url = get_auth_config().llm_url.rstrip("/")
    upstream_payload: dict[str, Any] = {
        "model": resolved_model_id or requested_model_id,
        "input": messages,
    }
    if max_tokens is not None:
        upstream_payload["max_tokens"] = max_tokens
    if temperature is not None:
        upstream_payload["temperature"] = temperature

    llm_response, status_code = http_json_request(f"{llm_url}/v1/chat/completions", upstream_payload)
    if (
        status_code == 404
        and upstream_payload["model"] != _LOCAL_LLM_MODEL_ID
        and _is_model_not_found_error(llm_response)
        and _can_use_local_llm_fallback(str(upstream_payload["model"]))
    ):
        fallback_payload = dict(upstream_payload)
        fallback_payload["model"] = _LOCAL_LLM_MODEL_ID
        return http_json_request(f"{llm_url}/v1/chat/completions", fallback_payload)
    return llm_response, status_code
