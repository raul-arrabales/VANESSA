from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

_VALID_STATUSES = {"queued", "running", "succeeded", "failed", "blocked", "cancelled"}
_VALID_PROFILES = {"online", "offline", "air_gapped"}


def _as_iso8601(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return text
    raise ValueError("invalid_timestamp")


def _as_runtime_profile(value: Any) -> str:
    profile = str(value or "").strip().lower()
    if profile not in _VALID_PROFILES:
        raise ValueError("invalid_runtime_profile")
    return profile


def _as_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status not in _VALID_STATUSES:
        raise ValueError("invalid_status")
    return status


def _as_object(value: Any, *, allow_none: bool = False) -> dict[str, Any] | None:
    if value is None and allow_none:
        return None
    if isinstance(value, dict):
        return value
    raise ValueError("invalid_object")


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

        created_at = _as_iso8601(payload.get("created_at"))
        if created_at is None:
            raise ValueError("invalid_created_at")

        return cls(
            id=execution_id,
            status=_as_status(payload.get("status")),
            agent_ref=agent_ref,
            agent_version=agent_version,
            model_ref=model_ref,
            runtime_profile=_as_runtime_profile(payload.get("runtime_profile")),
            created_at=created_at,
            started_at=_as_iso8601(payload.get("started_at")),
            finished_at=_as_iso8601(payload.get("finished_at")),
            result=_as_object(payload.get("result"), allow_none=True),
            error=_as_object(payload.get("error"), allow_none=True),
        )

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

