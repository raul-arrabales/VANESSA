from __future__ import annotations

import hashlib
import http.client
import json
import queue
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote, urlencode

DEFAULT_LOG_TAIL_LINES = 200
MAX_LOG_TAIL_LINES = 1000
DOCKER_SOCKET_PATH = "/var/run/docker.sock"
_SERVICE_REGISTRY_RELATIVE_PATH = Path("ops/local-staging/services.txt")
_FALLBACK_SERVICES = (
    "frontend",
    "backend",
    "llm",
    "llm_runtime_inference",
    "llm_runtime_embeddings",
    "llama_cpp",
    "qdrant",
    "image_analysis",
    "image_analysis_anpr",
    "image_analysis_objects",
    "image_analysis_captioning",
    "image_generation",
    "image_generation_text_to_image",
    "image_generation_plate_logo",
    "searxng",
    "mcp_gateway",
    "agent_engine",
    "sandbox",
    "kws",
    "weaviate",
    "postgres",
)
_DISPLAY_NAMES = {
    "frontend": "Frontend",
    "backend": "Backend",
    "llm": "LLM API",
    "llm_runtime_inference": "LLM Runtime Inference",
    "llm_runtime_embeddings": "LLM Runtime Embeddings",
    "llama_cpp": "llama.cpp",
    "qdrant": "Qdrant",
    "image_analysis": "Image Analysis",
    "image_analysis_anpr": "Image Analysis ANPR Worker",
    "image_analysis_objects": "Image Analysis Objects Worker",
    "image_analysis_captioning": "Image Analysis Captioning Worker",
    "image_generation": "Image Generation",
    "image_generation_text_to_image": "Image Generation Text-to-Image Worker",
    "image_generation_plate_logo": "Image Generation Plate Logo Worker",
    "searxng": "SearXNG Web Search",
    "mcp_gateway": "MCP Gateway",
    "agent_engine": "Agent Engine",
    "sandbox": "Sandbox",
    "kws": "KWS",
    "weaviate": "Weaviate",
    "postgres": "PostgreSQL",
}
_LEVEL_PATTERNS = (
    ("error", ("[error]", " error ", "exception", "traceback", "fatal")),
    ("warning", ("[warn]", "[warning]", " warning ", "deprecated")),
    ("info", ("[info]", " info ", " started ", " starting ", " listening ", " ready")),
    ("debug", ("[debug]", " debug ")),
)
_EVENT_TYPE_PATTERNS = (
    ("health", ("health", "readiness", "liveness")),
    ("http", ("get /", "post /", "put /", "patch /", "delete /", " http/")),
    ("startup", ("starting", "started", "listening", "boot", "ready")),
    ("runtime", ("runtime", "worker", "thread", "process")),
    ("model", ("model", "tokenizer", "embedding", "inference", "checkpoint")),
)


class ServiceLogsError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 503):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class _UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 5.0):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._socket_path)


@dataclass(frozen=True)
class _DockerContainerRef:
    id: str
    service: str


def list_available_services() -> list[dict[str, str]]:
    return [
        {
            "id": service,
            "display_name": _DISPLAY_NAMES.get(service, _humanize_service_name(service)),
        }
        for service in _load_service_registry()
    ]


def get_service_log_snapshot(
    service: str,
    *,
    tail_lines: int = DEFAULT_LOG_TAIL_LINES,
    since: datetime | None = None,
    level: str | None = None,
) -> dict[str, Any]:
    normalized_service = _normalize_service_name(service)
    _ensure_service_allowed(normalized_service)
    tail = _normalize_tail_lines(tail_lines)
    entries = list(_read_entries_from_docker(normalized_service, tail_lines=tail, since=since, follow=False, level=level))
    return {
        "service": normalized_service,
        "display_name": _DISPLAY_NAMES.get(normalized_service, _humanize_service_name(normalized_service)),
        "tail": tail,
        "entries": entries,
    }


def stream_service_log_entries(
    service: str,
    *,
    since: datetime | None = None,
    level: str | None = None,
) -> Iterator[dict[str, Any] | None]:
    normalized_service = _normalize_service_name(service)
    _ensure_service_allowed(normalized_service)

    event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
    error_queue: queue.Queue[ServiceLogsError] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            for entry in _read_entries_from_docker(normalized_service, tail_lines=0, since=since, follow=True, level=level):
                event_queue.put(entry)
        except ServiceLogsError as exc:
            error_queue.put(exc)
        finally:
            event_queue.put(None)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    while True:
        try:
            item = event_queue.get(timeout=10)
        except queue.Empty:
            yield None
            continue
        if item is None:
            if not error_queue.empty():
                raise error_queue.get()
            break
        yield item


def parse_iso8601_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ServiceLogsError("invalid_since", "The since value must be an ISO-8601 timestamp.", status_code=400) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_service_registry() -> list[str]:
    for path in _service_registry_candidates():
        if not path.exists():
            continue
        services = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if services:
            return services
    return list(_FALLBACK_SERVICES)


def _service_registry_candidates() -> tuple[Path, ...]:
    current_file = Path(__file__).resolve()
    return (
        current_file.parents[3] / _SERVICE_REGISTRY_RELATIVE_PATH,
        current_file.parents[4] / _SERVICE_REGISTRY_RELATIVE_PATH,
        Path("/app") / _SERVICE_REGISTRY_RELATIVE_PATH,
    )


def _normalize_service_name(value: str) -> str:
    return value.strip()


def _ensure_service_allowed(service: str) -> None:
    if service not in set(_load_service_registry()):
        raise ServiceLogsError("unknown_service", f"Unknown service '{service}'.", status_code=404)


def _normalize_tail_lines(value: int) -> int:
    return max(0, min(int(value), MAX_LOG_TAIL_LINES))


def _read_entries_from_docker(
    service: str,
    *,
    tail_lines: int,
    since: datetime | None,
    follow: bool,
    level: str | None,
) -> Iterator[dict[str, Any]]:
    container = _resolve_container(service)
    conn = _UnixSocketHTTPConnection(DOCKER_SOCKET_PATH, timeout=5.0)
    try:
        query = {
            "stdout": "1",
            "stderr": "1",
            "timestamps": "1",
            "follow": "1" if follow else "0",
            "tail": str(tail_lines),
        }
        if since is not None:
            query["since"] = str(max(0, int(since.timestamp())))
        conn.request("GET", f"/containers/{container.id}/logs?{urlencode(query)}")
        response = conn.getresponse()
        if response.status >= 400:
            raise ServiceLogsError(
                "service_logs_unavailable",
                f"Docker logs are unavailable for service '{service}'.",
                status_code=503,
            )
    except FileNotFoundError as exc:
        raise ServiceLogsError(
            "service_logs_unavailable",
            "Docker socket is unavailable in this backend environment.",
            status_code=503,
        ) from exc
    except OSError as exc:
        raise ServiceLogsError(
            "service_logs_unavailable",
            "Docker socket is unavailable in this backend environment.",
            status_code=503,
        ) from exc
    try:
        for index, raw_line in enumerate(_iter_response_lines(response)):
            entry = _build_log_entry(service, raw_line, index=index)
            if _entry_matches_filters(entry, since=since, level=level):
                yield entry
    finally:
        conn.close()


def _resolve_container(service: str) -> _DockerContainerRef:
    filters = quote(json.dumps({"label": [f"com.docker.compose.service={service}"]}, separators=(",", ":")))
    payload = _docker_json(f"/containers/json?all=1&filters={filters}")
    if not isinstance(payload, list) or not payload:
        raise ServiceLogsError(
            "service_logs_unavailable",
            f"No Docker container is available for service '{service}'.",
            status_code=503,
        )
    container_id = str(payload[0].get("Id", "")).strip()
    if not container_id:
        raise ServiceLogsError(
            "service_logs_unavailable",
            f"Docker container metadata is unavailable for service '{service}'.",
            status_code=503,
        )
    return _DockerContainerRef(id=container_id, service=service)


def _docker_json(path: str) -> Any:
    conn = _UnixSocketHTTPConnection(DOCKER_SOCKET_PATH, timeout=5.0)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        raw = response.read()
    except FileNotFoundError as exc:
        raise ServiceLogsError(
            "service_logs_unavailable",
            "Docker socket is unavailable in this backend environment.",
            status_code=503,
        ) from exc
    except OSError as exc:
        raise ServiceLogsError(
            "service_logs_unavailable",
            "Docker socket is unavailable in this backend environment.",
            status_code=503,
        ) from exc
    finally:
        conn.close()
    if response.status >= 400:
        raise ServiceLogsError("service_logs_unavailable", "Docker API request failed.", status_code=503)
    return json.loads(raw.decode("utf-8"))


def _iter_response_lines(response: http.client.HTTPResponse) -> Iterator[str]:
    text_buffer = ""
    for payload in _iter_decoded_payload_chunks(response):
        text_buffer += payload.decode("utf-8", errors="replace")
        while "\n" in text_buffer:
            line, text_buffer = text_buffer.split("\n", 1)
            yield line.rstrip("\r")
    if text_buffer:
        yield text_buffer.rstrip("\r")


def _iter_decoded_payload_chunks(response: http.client.HTTPResponse) -> Iterator[bytes]:
    frame_buffer = bytearray()
    framing_mode: bool | None = None

    while True:
        try:
            chunk = response.read(4096)
        except socket.timeout:
            continue
        if not chunk:
            break
        frame_buffer.extend(chunk)

        if framing_mode is None and len(frame_buffer) >= 8:
            framing_mode = frame_buffer[0] in (1, 2, 3) and frame_buffer[1:4] == b"\x00\x00\x00"

        if framing_mode is False:
            yield bytes(frame_buffer)
            frame_buffer.clear()
            continue

        while len(frame_buffer) >= 8:
            header = bytes(frame_buffer[:8])
            if header[0] not in (1, 2, 3) or header[1:4] != b"\x00\x00\x00":
                yield bytes(frame_buffer)
                frame_buffer.clear()
                framing_mode = False
                break
            frame_length = int.from_bytes(header[4:8], byteorder="big")
            if len(frame_buffer) < 8 + frame_length:
                break
            yield bytes(frame_buffer[8:8 + frame_length])
            del frame_buffer[:8 + frame_length]

    if frame_buffer:
        yield bytes(frame_buffer)


def _build_log_entry(service: str, raw_line: str, *, index: int) -> dict[str, Any]:
    timestamp, message = _split_timestamp(raw_line)
    level = _infer_level(message)
    event_type = _infer_event_type(message)
    digest = hashlib.sha1(f"{service}|{timestamp or ''}|{raw_line}|{index}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"{service}-{digest}",
        "service": service,
        "timestamp": timestamp,
        "level": level,
        "event_type": event_type,
        "raw": raw_line,
        "message": message,
    }


def _split_timestamp(raw_line: str) -> tuple[str | None, str]:
    stripped = raw_line.strip()
    if not stripped:
        return None, ""
    first_space = stripped.find(" ")
    if first_space <= 0:
        return None, stripped
    candidate = stripped[:first_space]
    try:
        parsed = parse_iso8601_timestamp(candidate)
    except ServiceLogsError:
        parsed = None
    if parsed is None:
        return None, stripped
    return parsed.isoformat().replace("+00:00", "Z"), stripped[first_space + 1 :].strip()


def _infer_level(message: str) -> str:
    lower_message = f" {message.lower()} "
    for level, fragments in _LEVEL_PATTERNS:
        if any(fragment in lower_message for fragment in fragments):
            return level
    return "unknown"


def _infer_event_type(message: str) -> str:
    lower_message = message.lower()
    for event_type, fragments in _EVENT_TYPE_PATTERNS:
        if any(fragment in lower_message for fragment in fragments):
            return event_type
    return "generic"


def _entry_matches_filters(entry: dict[str, Any], *, since: datetime | None, level: str | None) -> bool:
    if level and entry["level"] != level:
        return False
    if since is None:
        return True
    timestamp = parse_iso8601_timestamp(entry.get("timestamp"))
    if timestamp is None:
        return False
    return timestamp >= since


def _humanize_service_name(service: str) -> str:
    return service.replace("_", " ").title()
