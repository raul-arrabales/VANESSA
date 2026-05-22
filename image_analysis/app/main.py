from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import gateway as _gateway_module
from . import payloads as _payloads_module
from . import resources as _resources_module
from . import runtime as _runtime_module
from .constants import (
    COCO_LABELS,
    DEFAULT_CAPTION_MODEL_ID,
    DEFAULT_PORT,
    ROLE_ANPR,
    ROLE_CAPTIONING,
    ROLE_GATEWAY,
    ROLE_OBJECTS,
    ROLE_TASKS,
    SERVICE_VERSION,
    TASK_ROLE,
    VALID_ROLES,
    VALID_TASKS,
)
from .florence_compat import (
    patch_florence2_model_compat as _patch_florence2_model_compat,
)
from .florence_compat import (
    patch_florence2_transformers_config as _patch_florence2_transformers_config,
)
from .florence_compat import (
    patch_florence2_transformers_model as _patch_florence2_transformers_model,
)
from .florence_compat import (
    patch_florence2_transformers_tokenizer as _patch_florence2_transformers_tokenizer,
)
from .florence_compat import (
    resize_caption_token_embeddings as _resize_caption_token_embeddings,
)
from .workers import anpr as _anpr_module
from .workers import captioning as _captioning_module
from .workers import objects as _objects_module

Image = _payloads_module.Image

_fake_mode = _payloads_module.fake_mode
_resource_id = _payloads_module.resource_id
_decode_image = _payloads_module.decode_image
_normalize_tasks = _payloads_module.normalize_tasks
_box = _payloads_module.box
_normalized_box = _payloads_module.normalized_box
_float_option = _payloads_module.float_option
_int_option = _payloads_module.int_option
_runtime_defaults = _payloads_module.runtime_defaults
_as_float = _payloads_module.as_float
_as_box_xyxy = _payloads_module.as_box_xyxy
_empty_response = _payloads_module.empty_response
_fake_analyze = _payloads_module.fake_analyze

_resources = _resources_module.resources
_resources_for_role = _resources_module.resources_for_role

_load_alpr = _anpr_module.load_alpr
_plate_results = _anpr_module.plate_results
_load_object_detector = _objects_module.load_object_detector
_object_results = _objects_module.object_results
_load_captioner = _captioning_module.load_captioner
_model_tensor_context = _captioning_module.model_tensor_context
_caption_image_size = _captioning_module.caption_image_size
_caption_max_tokens = _captioning_module.caption_max_tokens
_caption_num_beams = _captioning_module.caption_num_beams
_square_caption_image = _captioning_module.square_caption_image
_caption_result = _captioning_module.caption_result

_worker_url = _gateway_module.worker_url
_worker_timeout = _gateway_module.worker_timeout
_gateway_health_worker_timeout = _gateway_module.gateway_health_worker_timeout
_http_json = _gateway_module.http_json
_worker_warning = _gateway_module.worker_warning
_merge_worker_response = _gateway_module.merge_worker_response
_gateway_worker_analyze = _gateway_module.gateway_worker_analyze
_worker_health = _gateway_module.worker_health
_health_for_role = _gateway_module.health_for_role
_resources_from_worker = _gateway_module.resources_from_worker
_resources_payload_for_role = _gateway_module.resources_payload_for_role

_analyze_local = _runtime_module.analyze_local
_analyze_for_role = _runtime_module.analyze_for_role
_analyze = _gateway_module.analyze


def _service_role() -> str:
    role = os.getenv("IMAGE_ANALYSIS_ROLE", ROLE_GATEWAY).strip().lower() or ROLE_GATEWAY
    return role if role in VALID_ROLES else ROLE_GATEWAY


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return None
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAImageAnalysis/0.1"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        role = _service_role()
        if self.path == "/health":
            self._send_json(_health_for_role(role))
            return
        if self.path == "/v1/resources":
            self._send_json(_resources_payload_for_role(role))
            return
        self._send_json({"error": "not_found", "message": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/v1/analyze":
            self._send_json({"error": "not_found", "message": "Not found"}, 404)
            return
        role = _service_role()
        payload = _read_json(self)
        if payload is None:
            self._send_json({"error": "invalid_payload", "message": "Expected JSON object"}, 400)
            return
        result, status = _analyze_for_role(payload, role)
        self._send_json(result, status)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if os.getenv("IMAGE_ANALYSIS_ACCESS_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)


def main() -> None:
    port = int(os.getenv("IMAGE_ANALYSIS_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"image_analysis role={_service_role()} listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
