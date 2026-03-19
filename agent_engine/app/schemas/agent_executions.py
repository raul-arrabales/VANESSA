from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

VALID_STATUSES = {"queued", "running", "succeeded", "failed", "blocked", "cancelled"}
VALID_RUNTIME_PROFILES = {"online", "offline"}


def ensure_runtime_profile(value: Any) -> str:
    profile = str(value or "").strip().lower()
    if profile == "air_gapped":
        return "offline"
    if profile not in VALID_RUNTIME_PROFILES:
        raise ValueError("invalid_runtime_profile")
    return profile


def ensure_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError("invalid_status")
    return status


def ensure_iso8601(value: Any, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("invalid_timestamp")
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            if required:
                raise ValueError("invalid_timestamp")
            return None
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return text
    raise ValueError("invalid_timestamp")


@dataclass(frozen=True)
class AgentExecutionRecord:
    id: str
    status: str
    agent_ref: str
    agent_version: str
    model_ref: str | None
    runtime_profile: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "agent_ref": self.agent_ref,
            "agent_version": self.agent_version,
            "model_ref": self.model_ref,
            "runtime_profile": self.runtime_profile,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AgentExecutionRecord":
        execution_id = str(payload.get("id", "")).strip()
        if not execution_id:
            raise ValueError("invalid_execution_id")

        agent_ref = str(payload.get("agent_ref", "")).strip()
        if not agent_ref:
            raise ValueError("invalid_agent_ref")

        agent_version = str(payload.get("agent_version", "")).strip()
        if not agent_version:
            raise ValueError("invalid_agent_version")

        model_ref_raw = payload.get("model_ref")
        model_ref = None
        if model_ref_raw is not None:
            model_ref_text = str(model_ref_raw).strip()
            model_ref = model_ref_text if model_ref_text else None

        result = payload.get("result")
        if result is not None and not isinstance(result, dict):
            raise ValueError("invalid_result")
        error = payload.get("error")
        if error is not None and not isinstance(error, dict):
            raise ValueError("invalid_error")

        return cls(
            id=execution_id,
            status=ensure_status(payload.get("status")),
            agent_ref=agent_ref,
            agent_version=agent_version,
            model_ref=model_ref,
            runtime_profile=ensure_runtime_profile(payload.get("runtime_profile")),
            created_at=ensure_iso8601(payload.get("created_at"), required=True),
            started_at=ensure_iso8601(payload.get("started_at")),
            finished_at=ensure_iso8601(payload.get("finished_at")),
            result=result,
            error=error,
        )
