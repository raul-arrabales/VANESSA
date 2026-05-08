from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
from os import PathLike
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from ..config import AuthConfig, get_auth_config

logger = logging.getLogger(__name__)

CLOUD_TRAFFIC_DIRECTIONS = {"egress", "ingress"}
CLOUD_TRAFFIC_EVENT_FIELDS = {
    "id",
    "timestamp",
    "direction",
    "phase",
    "runtime_profile",
    "source_service",
    "capability",
    "operation",
    "provider_origin",
    "provider_key",
    "provider_slug",
    "endpoint_host",
    "status_code",
    "duration_ms",
    "request_id",
}
_MAX_TEXT_FIELD_LENGTH = 256
_SUBSCRIBERS: set[Queue[dict[str, Any]]] = set()
_SUBSCRIBERS_LOCK = Lock()
_LOG_LOCK = Lock()


def publish_cloud_traffic_event(raw_event: dict[str, Any], *, config: AuthConfig | None = None) -> dict[str, Any]:
    event = sanitize_cloud_traffic_event(raw_event)
    _append_cloud_traffic_log(event, config=config)
    with _SUBSCRIBERS_LOCK:
        subscribers = list(_SUBSCRIBERS)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(event)
        except Exception:
            logger.debug("Unable to publish cloud traffic event to subscriber", exc_info=True)
    return event


def sanitize_cloud_traffic_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    direction = _clean_text(raw_event.get("direction"), max_length=16)
    if direction not in CLOUD_TRAFFIC_DIRECTIONS:
        raise ValueError("Cloud traffic direction must be 'egress' or 'ingress'")

    event: dict[str, Any] = {
        "id": _clean_text(raw_event.get("id"), max_length=96) or uuid4().hex,
        "timestamp": _clean_text(raw_event.get("timestamp"), max_length=64) or _iso_now(),
        "direction": direction,
        "phase": _clean_text(raw_event.get("phase"), max_length=96) or "request",
        "runtime_profile": _clean_text(raw_event.get("runtime_profile"), max_length=32) or "online",
        "source_service": _clean_text(raw_event.get("source_service"), max_length=64) or "backend",
        "capability": _clean_text(raw_event.get("capability"), max_length=64),
        "operation": _clean_text(raw_event.get("operation"), max_length=96),
        "provider_origin": _clean_text(raw_event.get("provider_origin"), max_length=32),
        "provider_key": _clean_text(raw_event.get("provider_key"), max_length=96),
        "provider_slug": _clean_text(raw_event.get("provider_slug"), max_length=96),
        "endpoint_host": _clean_endpoint_host(raw_event.get("endpoint_host")),
    }

    status_code = _clean_int(raw_event.get("status_code"))
    duration_ms = _clean_int(raw_event.get("duration_ms"))
    request_id = _clean_text(raw_event.get("request_id"), max_length=128)
    if status_code is not None:
        event["status_code"] = status_code
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if request_id:
        event["request_id"] = request_id
    return {key: value for key, value in event.items() if key in CLOUD_TRAFFIC_EVENT_FIELDS and value not in {None, ""}}


@contextmanager
def subscribe_cloud_traffic_events() -> Iterator[Queue[dict[str, Any]]]:
    queue: Queue[dict[str, Any]] = Queue(maxsize=256)
    with _SUBSCRIBERS_LOCK:
        _SUBSCRIBERS.add(queue)
    try:
        yield queue
    finally:
        with _SUBSCRIBERS_LOCK:
            _SUBSCRIBERS.discard(queue)


def stream_cloud_traffic_events(*, heartbeat_seconds: float = 15.0) -> Iterator[dict[str, Any] | None]:
    with subscribe_cloud_traffic_events() as queue:
        while True:
            try:
                yield queue.get(timeout=heartbeat_seconds)
            except Empty:
                yield None


def endpoint_host_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    return parsed.netloc if parsed.netloc else str(url or "").split("/", 1)[0][: _MAX_TEXT_FIELD_LENGTH]


def request_id_from_headers(headers: dict[str, Any] | None) -> str | None:
    if not isinstance(headers, dict):
        return None
    for key in ("x-request-id", "x-openai-request-id", "openai-request-id", "request-id", "cf-ray"):
        value = headers.get(key) or headers.get(key.title())
        normalized = _clean_text(value, max_length=128)
        if normalized:
            return normalized
    return None


def _append_cloud_traffic_log(event: dict[str, Any], *, config: AuthConfig | None) -> None:
    resolved_config = config
    if resolved_config is None:
        try:
            resolved_config = get_auth_config()
        except Exception:
            return
    if not bool(getattr(resolved_config, "cloud_traffic_log_enabled", False)):
        return
    raw_path = str(getattr(resolved_config, "cloud_traffic_log_path", "") or "").strip()
    if not raw_path:
        return
    max_bytes = int(getattr(resolved_config, "cloud_traffic_log_max_bytes", 10_485_760) or 10_485_760)
    try:
        with _LOG_LOCK:
            _append_jsonl_with_rotation(raw_path, event, max_bytes=max_bytes)
    except Exception:
        logger.warning("Unable to append cloud traffic log", exc_info=True)


def _append_jsonl_with_rotation(path: str | PathLike[str], event: dict[str, Any], *, max_bytes: int) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if max_bytes > 0 and log_path.exists() and log_path.stat().st_size >= max_bytes:
        rotated_path = log_path.with_name(f"{log_path.name}.1")
        if rotated_path.exists():
            rotated_path.unlink()
        log_path.rename(rotated_path)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _clean_text(value: Any, *, max_length: int = _MAX_TEXT_FIELD_LENGTH) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized[:max_length]


def _clean_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _clean_endpoint_host(value: Any) -> str | None:
    normalized = _clean_text(value)
    if not normalized:
        return None
    if "://" in normalized:
        return endpoint_host_from_url(normalized)
    return normalized.split("/", 1)[0][: _MAX_TEXT_FIELD_LENGTH]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "CLOUD_TRAFFIC_DIRECTIONS",
    "CLOUD_TRAFFIC_EVENT_FIELDS",
    "endpoint_host_from_url",
    "publish_cloud_traffic_event",
    "request_id_from_headers",
    "sanitize_cloud_traffic_event",
    "stream_cloud_traffic_events",
    "subscribe_cloud_traffic_events",
]
