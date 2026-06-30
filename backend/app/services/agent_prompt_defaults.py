from __future__ import annotations

from typing import Any

from .user_agent_types import USER_AGENT_TYPE_WORKFLOW
from vanessa_shared.workflow_prompt_contract import (
    default_agent_runtime_prompts as shared_default_agent_runtime_prompts,
    default_runtime_prompts_for_agent_type as shared_default_runtime_prompts_for_agent_type,
    normalize_agent_runtime_prompts as shared_normalize_agent_runtime_prompts,
)

RETRIEVAL_CONTEXT_PREVIEW = "\n".join(
    [
        "Reference [1] title={retrieved title} file={retrieved file}",
        "Chunk id={retrieved chunk id} metadata={retrieved metadata}",
        "{retrieved text}",
    ]
)


def default_agent_runtime_prompts() -> dict[str, str]:
    return shared_default_agent_runtime_prompts()


def _retrieval_context_required(agent_type: Any) -> bool:
    normalized = str(agent_type or "").strip().lower()
    return normalized != USER_AGENT_TYPE_WORKFLOW


def _default_runtime_prompts_for_agent_type(agent_type: Any) -> dict[str, str]:
    if _retrieval_context_required(agent_type):
        return default_agent_runtime_prompts()
    return shared_default_runtime_prompts_for_agent_type(agent_type)


def normalize_agent_runtime_prompts(value: Any, *, agent_type: Any = None) -> dict[str, str]:
    return shared_normalize_agent_runtime_prompts(value, agent_type=agent_type)


def coerce_agent_runtime_prompts(value: Any, *, default_when_missing: bool, agent_type: Any = None) -> dict[str, str]:
    if value is None:
        if default_when_missing:
            return _default_runtime_prompts_for_agent_type(agent_type)
        raise ValueError("runtime_prompts is required")
    if not isinstance(value, dict):
        raise ValueError("runtime_prompts must be an object")

    retrieval_context = str(value.get("retrieval_context", "")).strip()
    if not retrieval_context and _retrieval_context_required(agent_type):
        raise ValueError("runtime_prompts.retrieval_context is required")
    normalized = normalize_agent_runtime_prompts(value, agent_type=agent_type)
    return {
        "retrieval_context": retrieval_context if retrieval_context else normalized["retrieval_context"],
    }


def build_agent_system_prompt_preview(spec: dict[str, Any]) -> dict[str, Any]:
    runtime_prompts = normalize_agent_runtime_prompts(
        spec.get("runtime_prompts"),
        agent_type=spec.get("agent_type"),
    )
    messages: list[dict[str, str]] = []
    text_sections: list[str] = []

    instructions = str(spec.get("instructions") or "").strip()
    if instructions:
        messages.append(
            {
                "role": "system",
                "label": "agent_instructions",
                "content": instructions,
            }
        )
        text_sections.append("\n".join(["System message: agent instructions", instructions]))

    retrieval_context = runtime_prompts["retrieval_context"]
    if retrieval_context:
        retrieval_content = "\n\n".join([retrieval_context, RETRIEVAL_CONTEXT_PREVIEW])
        messages.append(
            {
                "role": "system",
                "label": "retrieval_context",
                "content": retrieval_content,
            }
        )
        text_sections.append("\n".join(["System message: retrieval context", retrieval_content]))

    if str(spec.get("agent_type") or "").strip().lower() == USER_AGENT_TYPE_WORKFLOW:
        workflow_definition = spec.get("workflow_definition") if isinstance(spec.get("workflow_definition"), dict) else {}
        actions = workflow_definition.get("actions") if isinstance(workflow_definition.get("actions"), list) else []
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            prompt = str(action.get("prompt") or "").strip()
            if not prompt:
                continue
            name = str(action.get("name") or action.get("type") or f"action_{index + 1}").strip() or f"action_{index + 1}"
            label = f"workflow_action_prompt_{index + 1}"
            messages.append(
                {
                    "role": "system",
                    "label": label,
                    "content": prompt,
                }
            )
            text_sections.append("\n".join([f"Workflow action prompt: {name}", prompt]))

    return {
        "messages": messages,
        "text": "\n\n---\n\n".join(text_sections),
    }
