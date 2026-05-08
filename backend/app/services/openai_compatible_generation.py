from __future__ import annotations

from typing import Any


_REQUEST_OPTION_KEYS = {
    "service_tier",
    "prompt_cache_key",
    "prompt_cache_retention",
}


def uses_chat_completion_token_budget(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized.startswith(("gpt-5", "o1", "o3", "o4"))


def add_openai_compatible_chat_generation_options(
    payload: dict[str, Any],
    *,
    model: str,
    request_format: str,
    token_budget: int | None,
    temperature: float | None,
) -> None:
    uses_chat_completion_budget = (
        request_format.strip().lower() == "openai_chat"
        and uses_chat_completion_token_budget(model)
    )
    if token_budget is not None:
        token_budget_key = "max_completion_tokens" if uses_chat_completion_budget else "max_tokens"
        payload[token_budget_key] = token_budget
    if temperature is not None and not uses_chat_completion_budget:
        payload["temperature"] = temperature


def add_openai_compatible_request_options(
    payload: dict[str, Any],
    *,
    config: dict[str, Any],
    request_format: str,
    stream: bool = False,
) -> None:
    options = config.get("request_options") if isinstance(config.get("request_options"), dict) else {}
    merged_options = {**{key: config.get(key) for key in _REQUEST_OPTION_KEYS | {"reasoning_effort"}}, **options}
    for key in _REQUEST_OPTION_KEYS:
        value = merged_options.get(key)
        if value is not None and value != "":
            payload[key] = value

    reasoning_effort = merged_options.get("reasoning_effort")
    if reasoning_effort is not None and reasoning_effort != "":
        if request_format.strip().lower() == "openai_chat":
            payload["reasoning_effort"] = reasoning_effort
        else:
            existing_reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), dict) else {}
            payload["reasoning"] = {**existing_reasoning, "effort": reasoning_effort}

    stream_options = config.get("stream_options") if isinstance(config.get("stream_options"), dict) else None
    if stream and stream_options:
        payload["stream_options"] = dict(stream_options)
