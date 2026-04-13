from __future__ import annotations

from typing import Any


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
