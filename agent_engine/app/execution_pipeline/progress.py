from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any, Callable
from uuid import uuid4

ProgressEmitter = Callable[[dict[str, Any]], None]

_MAX_DETAIL_TEXT = 600
_MAX_RESULTS = 3


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trim_text(value: Any, *, limit: int = _MAX_DETAIL_TEXT) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 0)].rstrip()}..."


def summarize_results(results: Any) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        return []
    summarized: list[dict[str, Any]] = []
    for item in results[:_MAX_RESULTS]:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        summarized.append(
            {
                "id": str(item.get("id") or "").strip(),
                "title": str(
                    metadata.get("title")
                    or metadata.get("source_display_name")
                    or metadata.get("source_name")
                    or metadata.get("source_path")
                    or item.get("title")
                    or ""
                ).strip(),
                "snippet": trim_text(item.get("snippet") or item.get("text"), limit=220),
            }
        )
    return summarized


def compact_payload(value: Any, *, limit: int = _MAX_DETAIL_TEXT) -> Any:
    if isinstance(value, dict):
        return {str(key): compact_payload(item, limit=limit) for key, item in value.items()}
    if isinstance(value, list):
        return [compact_payload(item, limit=limit) for item in value[:_MAX_RESULTS]]
    if isinstance(value, str):
        return trim_text(value, limit=limit)
    return value


class ProgressRecorder:
    def __init__(self, emit: ProgressEmitter | None = None) -> None:
        self._emit = emit
        self._started_monotonic: dict[str, float] = {}
        self._started_at: dict[str, str] = {}

    def enabled(self) -> bool:
        return self._emit is not None

    def start(
        self,
        *,
        kind: str,
        label: str,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
        status_id: str | None = None,
    ) -> str:
        normalized_id = status_id or f"{kind}-{uuid4()}"
        started_at = iso_now()
        self._started_monotonic[normalized_id] = monotonic()
        self._started_at[normalized_id] = started_at
        self._send(
            {
                "id": normalized_id,
                "kind": kind,
                "label": label,
                "state": "running",
                "started_at": started_at,
                "completed_at": None,
                "duration_ms": None,
                "summary": summary,
                "details": details or {},
            }
        )
        return normalized_id

    def complete(
        self,
        status_id: str,
        *,
        kind: str,
        label: str,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        started = self._started_monotonic.pop(status_id, None)
        duration_ms = int((monotonic() - started) * 1000) if started is not None else None
        self._send(
            {
                "id": status_id,
                "kind": kind,
                "label": label,
                "state": "completed",
                "started_at": self._started_at.pop(status_id, None),
                "completed_at": iso_now(),
                "duration_ms": duration_ms,
                "summary": summary,
                "details": details or {},
            }
        )

    def fail(
        self,
        status_id: str,
        *,
        kind: str,
        label: str,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if status_id not in self._started_monotonic and status_id not in self._started_at:
            return
        started = self._started_monotonic.pop(status_id, None)
        duration_ms = int((monotonic() - started) * 1000) if started is not None else None
        self._send(
            {
                "id": status_id,
                "kind": kind,
                "label": label,
                "state": "failed",
                "started_at": self._started_at.pop(status_id, None),
                "completed_at": iso_now(),
                "duration_ms": duration_ms,
                "summary": summary,
                "details": details or {},
            }
        )

    def _send(self, payload: dict[str, Any]) -> None:
        if self._emit is None:
            return
        self._emit(payload)
