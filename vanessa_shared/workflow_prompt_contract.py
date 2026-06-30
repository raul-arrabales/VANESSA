from __future__ import annotations

from typing import Any

WORKFLOW_AGENT_TYPE = "workflow"

DEFAULT_RETRIEVAL_CONTEXT_PROMPT = "\n".join(
    [
        "Use the following retrieved context if it is relevant to the user's request.",
        "When you use retrieved context, cite the supporting reference inline with bracketed numeric citations such as [1] or [1, 2].",
        "Do not cite a reference unless it supports the sentence that uses the citation.",
    ]
)

def default_agent_runtime_prompts() -> dict[str, str]:
    return {
        "retrieval_context": DEFAULT_RETRIEVAL_CONTEXT_PROMPT,
    }


def default_runtime_prompts_for_agent_type(agent_type: Any) -> dict[str, str]:
    normalized_agent_type = str(agent_type or "").strip().lower()
    if normalized_agent_type == WORKFLOW_AGENT_TYPE:
        return {
            "retrieval_context": "",
        }
    return default_agent_runtime_prompts()


def normalize_agent_runtime_prompts(value: Any, *, agent_type: Any = None) -> dict[str, str]:
    runtime_prompts = value if isinstance(value, dict) else {}
    defaults = default_runtime_prompts_for_agent_type(agent_type)
    return {
        "retrieval_context": str(runtime_prompts.get("retrieval_context") or defaults["retrieval_context"]).strip(),
    }
