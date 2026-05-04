from __future__ import annotations

from typing import Any

DEFAULT_RETRIEVAL_CONTEXT_PROMPT = "\n".join(
    [
        "Use the following retrieved context if it is relevant to the user's request.",
        "When you use retrieved context, cite the supporting reference inline with bracketed numeric citations such as [1] or [1, 2].",
        "Do not cite a reference unless it supports the sentence that uses the citation.",
    ]
)

RETRIEVAL_CONTEXT_PREVIEW = "\n".join(
    [
        "Reference [1] title={retrieved title} file={retrieved file}",
        "Chunk id={retrieved chunk id} metadata={retrieved metadata}",
        "{retrieved text}",
    ]
)


def default_agent_runtime_prompts() -> dict[str, str]:
    return {"retrieval_context": DEFAULT_RETRIEVAL_CONTEXT_PROMPT}


def normalize_agent_runtime_prompts(value: Any) -> dict[str, str]:
    runtime_prompts = value if isinstance(value, dict) else {}
    retrieval_context = str(runtime_prompts.get("retrieval_context") or "").strip()
    return {"retrieval_context": retrieval_context or DEFAULT_RETRIEVAL_CONTEXT_PROMPT}


def coerce_agent_runtime_prompts(value: Any, *, default_when_missing: bool) -> dict[str, str]:
    if value is None:
        if default_when_missing:
            return default_agent_runtime_prompts()
        raise ValueError("runtime_prompts is required")
    if not isinstance(value, dict):
        raise ValueError("runtime_prompts must be an object")

    retrieval_context = str(value.get("retrieval_context", "")).strip()
    if not retrieval_context:
        raise ValueError("runtime_prompts.retrieval_context is required")
    return {"retrieval_context": retrieval_context}


def build_agent_system_prompt_preview(spec: dict[str, Any]) -> dict[str, Any]:
    runtime_prompts = normalize_agent_runtime_prompts(spec.get("runtime_prompts"))
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

    return {
        "messages": messages,
        "text": "\n\n---\n\n".join(text_sections),
    }
