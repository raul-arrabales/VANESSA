from __future__ import annotations

from typing import Any

DEFAULT_RETRIEVAL_CONTEXT_PROMPT = "\n".join(
    [
        "Use the following retrieved context if it is relevant to the user's request.",
        "When you use retrieved context, cite the supporting reference inline with bracketed numeric citations such as [1] or [1, 2].",
        "Do not cite a reference unless it supports the sentence that uses the citation.",
    ]
)


def default_agent_runtime_prompts() -> dict[str, str]:
    return {"retrieval_context": DEFAULT_RETRIEVAL_CONTEXT_PROMPT}


def normalize_agent_runtime_prompts(value: Any) -> dict[str, str]:
    runtime_prompts = value if isinstance(value, dict) else {}
    retrieval_context = str(runtime_prompts.get("retrieval_context") or "").strip()
    return {"retrieval_context": retrieval_context or DEFAULT_RETRIEVAL_CONTEXT_PROMPT}
