from __future__ import annotations

from json import dumps
import logging
from time import monotonic
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from ..config import get_config

logger = logging.getLogger(__name__)


def report_cloud_traffic_for_binding(
    binding: dict[str, Any],
    *,
    direction: str,
    phase: str,
    capability: str,
    operation: str,
    endpoint_url: str,
    status_code: int | None = None,
    duration_ms: int | None = None,
    force_external: bool = False,
) -> None:
    provider_origin = str(binding.get("provider_origin") or "").strip().lower()
    if not force_external and provider_origin != "cloud":
        return
    report_cloud_traffic_event(
        {
            "direction": direction,
            "phase": phase,
            "runtime_profile": "online",
            "source_service": "agent_engine",
            "capability": capability,
            "operation": operation,
            "provider_origin": provider_origin or ("external" if force_external else None),
            "provider_key": binding.get("provider_key"),
            "provider_slug": binding.get("slug") or binding.get("provider_slug"),
            "endpoint_host": endpoint_host_from_url(endpoint_url),
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
    )


def report_cloud_traffic_event(event: dict[str, Any]) -> None:
    config = get_config()
    backend_url = config.backend_url.rstrip("/")
    if not backend_url or not config.agent_engine_service_token:
        return
    payload = dumps(_sanitize_event(event), separators=(",", ":")).encode("utf-8")
    req = request.Request(
        f"{backend_url}/v1/internal/cloud-traffic/events",
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Service-Token": config.agent_engine_service_token,
        },
        method="POST",
    )
    try:
        started = monotonic()
        with request.urlopen(req, timeout=0.2) as response:  # noqa: S310
            response.read()
        logger.debug("Reported cloud traffic event in %.2fms", (monotonic() - started) * 1000)
    except (TimeoutError, error.URLError, OSError):
        logger.debug("Unable to report cloud traffic event", exc_info=True)


def endpoint_host_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    return parsed.netloc if parsed.netloc else str(url or "").split("/", 1)[0][:256]


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    allowed = {
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
    return {key: value for key, value in event.items() if key in allowed and value not in {None, ""}}


__all__ = [
    "endpoint_host_from_url",
    "report_cloud_traffic_event",
    "report_cloud_traffic_for_binding",
]
