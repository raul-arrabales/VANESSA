from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..retrieval.types import RetrievalRequest


@dataclass(slots=True)
class ToolInvocation:
    tool_ref: str
    tool_name: str
    transport: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConversationState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    retrieval_request: RetrievalRequest | None = None


@dataclass(slots=True)
class ExecutionResult:
    output_text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    embedding_calls: list[dict[str, Any]] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    retrieval_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "output_text": self.output_text,
            "tool_calls": self.tool_calls,
            "embedding_calls": self.embedding_calls,
            "model_calls": self.model_calls,
            "retrieval_calls": self.retrieval_calls,
        }


@dataclass(slots=True)
class ExecutionContext:
    execution_id: str
    agent_id: str
    runtime_profile: str
    requested_by_user_id: int
    requested_by_role: str
    execution_input: dict[str, Any]
    platform_runtime: dict[str, Any] | None
    conversation: ConversationState
