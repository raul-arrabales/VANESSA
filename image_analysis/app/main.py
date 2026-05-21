from __future__ import annotations

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from typing import Any

try:  # pragma: no cover - optional dependency in lightweight test environments
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]

SERVICE_VERSION = "0.1.0"
VALID_TASKS = {"license_plate_recognition", "object_detection", "captioning"}
DEFAULT_PORT = 8090
_ALPR_PIPELINE: Any | None = None
_OBJECT_DETECTOR: Any | None = None
_CAPTIONER: tuple[Any, Any] | None = None

COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


def _fake_mode() -> bool:
    return os.getenv("IMAGE_ANALYSIS_FAKE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _resource_id(env_name: str, default: str) -> str:
    return os.getenv(env_name, default).strip() or default


def _resources() -> list[dict[str, Any]]:
    return [
        {
            "id": _resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            "display_name": "License plate detector",
            "provider_resource_id": _resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            "metadata": {"task_key": "image_plate_detection", "engine": "open-image-models"},
        },
        {
            "id": _resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
            "display_name": "License plate OCR",
            "provider_resource_id": _resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
            "metadata": {"task_key": "image_plate_ocr", "engine": "fast-plate-ocr"},
        },
        {
            "id": _resource_id("IMAGE_ANALYSIS_OBJECT_DETECTOR_MODEL_ID", "rfdetr-nano"),
            "display_name": "Object detector",
            "provider_resource_id": _resource_id("IMAGE_ANALYSIS_OBJECT_DETECTOR_MODEL_ID", "rfdetr-nano"),
            "metadata": {"task_key": "object_detection", "engine": "rf-detr"},
        },
        {
            "id": _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", "microsoft/Florence-2-large-ft"),
            "display_name": "Image captioner",
            "provider_resource_id": _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", "microsoft/Florence-2-large-ft"),
            "metadata": {"task_key": "image_captioning", "engine": "florence-2"},
        },
    ]


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


def _decode_image(payload: dict[str, Any]) -> tuple[bytes, int, int, Any | None, dict[str, Any] | None]:
    image_payload = payload.get("image")
    if not isinstance(image_payload, dict):
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image must be an object"}
    mime_type = str(image_payload.get("mime_type") or "").strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "unsupported image.mime_type"}
    data_base64 = str(image_payload.get("data_base64") or "").strip()
    if not data_base64:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image.data_base64 is required"}
    try:
        raw = base64.b64decode(data_base64, validate=True)
    except ValueError:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image.data_base64 is invalid"}
    if Image is None:
        return raw, 0, 0, None, None
    try:
        with Image.open(BytesIO(raw)) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
    except Exception:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image payload could not be decoded"}
    return raw, int(width), int(height), rgb_image, None


def _normalize_tasks(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return [], {"error": "invalid_tasks", "message": "tasks must be a non-empty array"}
    tasks = [str(item).strip().lower() for item in raw_tasks if str(item).strip()]
    invalid = sorted({task for task in tasks if task not in VALID_TASKS})
    if invalid:
        return [], {"error": "invalid_tasks", "message": "unsupported image analysis task", "tasks": invalid}
    return tasks, None


def _box(width: int, height: int) -> list[int]:
    w = max(width, 1)
    h = max(height, 1)
    return [max(0, w // 4), max(0, h // 3), max(1, (w * 3) // 4), max(1, h // 2)]


def _normalized_box(box: list[int], width: int, height: int) -> list[float]:
    w = max(width, 1)
    h = max(height, 1)
    return [round(box[0] / w, 6), round(box[1] / h, 6), round(box[2] / w, 6), round(box[3] / h, 6)]


def _float_option(payload: dict[str, Any], name: str, default: float) -> float:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    thresholds = payload.get("thresholds") if isinstance(payload.get("thresholds"), dict) else {}
    value = options.get(name, thresholds.get(name, default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_option(payload: dict[str, Any], name: str, default: int) -> int:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    value = options.get(name, payload.get(name, default))
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _runtime_defaults(payload: dict[str, Any]) -> dict[str, str]:
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    task_defaults = runtime.get("task_defaults") if isinstance(runtime.get("task_defaults"), dict) else {}
    return {str(key): str(value) for key, value in task_defaults.items() if str(value).strip()}


def _patch_florence2_transformers_config(pretrained_config_cls: Any) -> None:
    if not hasattr(pretrained_config_cls, "forced_bos_token_id"):
        setattr(pretrained_config_cls, "forced_bos_token_id", None)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_box_xyxy(value: Any) -> list[int] | None:
    if value is None:
        return None
    try:
        values = list(value)
    except TypeError:
        return None
    if len(values) < 4:
        return None
    return [int(round(float(values[index]))) for index in range(4)]


def _load_alpr() -> Any:
    global _ALPR_PIPELINE
    if _ALPR_PIPELINE is None:
        from fast_alpr import ALPR

        _ALPR_PIPELINE = ALPR(
            detector_model=_resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            ocr_model=_resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
        )
    return _ALPR_PIPELINE


def _plate_results(image: Any, width: int, height: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    import numpy as np

    detector_threshold = _float_option(payload, "plate_detector", 0.25)
    max_results = _int_option(payload, "max_license_plates", 20)
    model_defaults = _runtime_defaults(payload)
    pipeline = _load_alpr()
    frame_bgr = np.array(image)[:, :, ::-1]
    raw_results = pipeline.predict(frame_bgr)
    results: list[dict[str, Any]] = []
    for item in raw_results or []:
        detection = getattr(item, "detection", item)
        ocr = getattr(item, "ocr", None)
        confidence = _as_float(getattr(detection, "confidence", None), _as_float(getattr(item, "confidence", None), 0.0))
        if confidence < detector_threshold:
            continue
        box = _as_box_xyxy(getattr(detection, "bounding_box", None) or getattr(detection, "box", None) or getattr(item, "box", None))
        if box is None:
            continue
        text = str(getattr(ocr, "text", None) or getattr(item, "text", "") or "").strip()
        text_confidence = _as_float(getattr(ocr, "confidence", None), _as_float(getattr(item, "text_confidence", None), 0.0))
        results.append(
            {
                "text": text,
                "text_confidence": text_confidence,
                "box_xyxy": box,
                "box_normalized_xyxy": _normalized_box(box, width, height),
                "polygon": getattr(detection, "polygon", None),
                "plate_detector_model_id": model_defaults.get("plate_detector"),
                "plate_ocr_model_id": model_defaults.get("plate_ocr"),
            }
        )
        if len(results) >= max_results:
            break
    return results


def _load_object_detector() -> Any:
    global _OBJECT_DETECTOR
    if _OBJECT_DETECTOR is None:
        from rfdetr import RFDETRBase, RFDETRLarge, RFDETRNano, RFDETRSmall

        variant = os.getenv("IMAGE_ANALYSIS_RFDETR_VARIANT", "nano").strip().lower()
        model_cls = {
            "base": RFDETRBase,
            "small": RFDETRSmall,
            "large": RFDETRLarge,
            "nano": RFDETRNano,
        }.get(variant, RFDETRNano)
        _OBJECT_DETECTOR = model_cls()
    return _OBJECT_DETECTOR


def _object_results(image: Any, width: int, height: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    detector = _load_object_detector()
    threshold = _float_option(payload, "object_detection", 0.25)
    max_results = _int_option(payload, "max_objects", 50)
    model_defaults = _runtime_defaults(payload)
    raw = detector.predict(image, threshold=threshold)
    xyxy = getattr(raw, "xyxy", [])
    confidences = getattr(raw, "confidence", getattr(raw, "confidences", []))
    class_ids = getattr(raw, "class_id", getattr(raw, "class_ids", []))
    results: list[dict[str, Any]] = []
    for box_value, confidence_value, class_id_value in zip(xyxy, confidences, class_ids, strict=False):
        confidence = _as_float(confidence_value)
        if confidence < threshold:
            continue
        box = _as_box_xyxy(box_value)
        if box is None:
            continue
        class_index = int(class_id_value)
        label = COCO_LABELS[class_index] if 0 <= class_index < len(COCO_LABELS) else str(class_index)
        results.append(
            {
                "label": label,
                "confidence": confidence,
                "box_xyxy": box,
                "box_normalized_xyxy": _normalized_box(box, width, height),
                "object_detector_model_id": model_defaults.get("object_detector"),
            }
        )
        if len(results) >= max_results:
            break
    return results


def _load_captioner() -> tuple[Any, Any]:
    global _CAPTIONER
    if _CAPTIONER is None:
        from transformers import AutoModelForCausalLM, AutoProcessor, PretrainedConfig

        _patch_florence2_transformers_config(PretrainedConfig)

        model_id = _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", "microsoft/Florence-2-large-ft")
        model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        _CAPTIONER = (model, processor)
    return _CAPTIONER


def _caption_result(image: Any, width: int, height: int, payload: dict[str, Any]) -> dict[str, Any]:
    import torch

    model, processor = _load_captioner()
    task_prompt = os.getenv("IMAGE_ANALYSIS_FLORENCE_CAPTION_PROMPT", "<CAPTION>")
    inputs = processor(text=task_prompt, images=image, return_tensors="pt")
    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=_int_option(payload, "max_caption_tokens", 128),
            num_beams=3,
        )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(generated_text, task=task_prompt, image_size=(width, height))
    text = parsed.get(task_prompt, generated_text) if isinstance(parsed, dict) else generated_text
    return {"text": str(text).strip(), "captioner_model_id": _runtime_defaults(payload).get("captioner")}


def _analyze(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    _raw, width, height, image, error = _decode_image(payload)
    if error:
        return error, 400
    tasks, error = _normalize_tasks(payload)
    if error:
        return error, 400

    response: dict[str, Any] = {
        "image": {"width": width, "height": height},
        "license_plates": [],
        "objects": [],
        "caption": None,
        "model_resources": _runtime_defaults(payload),
        "warnings": [],
    }

    if _fake_mode():
        box = _box(width, height)
        if "license_plate_recognition" in tasks:
            response["license_plates"] = [
                {
                    "text": os.getenv("IMAGE_ANALYSIS_FAKE_PLATE_TEXT", "LOCAL123"),
                    "text_confidence": 0.99,
                    "box_xyxy": box,
                    "box_normalized_xyxy": _normalized_box(box, width, height),
                    "plate_detector_model_id": response["model_resources"].get("plate_detector"),
                    "plate_ocr_model_id": response["model_resources"].get("plate_ocr"),
                }
            ]
        if "object_detection" in tasks:
            response["objects"] = [
                {
                    "label": "vehicle",
                    "confidence": 0.95,
                    "box_xyxy": box,
                    "box_normalized_xyxy": _normalized_box(box, width, height),
                    "object_detector_model_id": response["model_resources"].get("object_detector"),
                }
            ]
        if "captioning" in tasks:
            response["caption"] = {
                "text": "A vehicle is visible in the image.",
                "captioner_model_id": response["model_resources"].get("captioner"),
            }
        response.pop("warnings", None)
        return response, 200

    if image is None:
        response["warnings"].append({"code": "image_runtime_unavailable", "message": "Pillow is unavailable"})
        return response, 200

    if "license_plate_recognition" in tasks:
        try:
            response["license_plates"] = _plate_results(image, width, height, payload)
        except Exception as exc:  # pragma: no cover - depends on optional model runtimes
            response["warnings"].append({"code": "plate_runtime_error", "message": str(exc)})
    if "object_detection" in tasks:
        try:
            response["objects"] = _object_results(image, width, height, payload)
        except Exception as exc:  # pragma: no cover
            response["warnings"].append({"code": "object_runtime_error", "message": str(exc)})
    if "captioning" in tasks:
        try:
            response["caption"] = _caption_result(image, width, height, payload)
        except Exception as exc:  # pragma: no cover
            response["warnings"].append({"code": "caption_runtime_error", "message": str(exc)})
            response["caption"] = {
                "text": "",
                "captioner_model_id": response["model_resources"].get("captioner"),
                "status": "model_runtime_error",
            }

    if not response["warnings"]:
        response.pop("warnings", None)

    return response, 200


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAImageAnalysis/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "image_analysis", "version": SERVICE_VERSION, "fake_mode": _fake_mode()})
            return
        if self.path == "/v1/resources":
            self._send_json(200, {"resources": _resources()})
            return
        self._send_json(404, {"error": "not_found", "message": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/analyze":
            self._send_json(404, {"error": "not_found", "message": "Not found"})
            return
        payload = _read_json(self)
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return
        result, status = _analyze(payload)
        self._send_json(status, result)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if os.getenv("IMAGE_ANALYSIS_ACCESS_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)


def main() -> None:
    port = int(os.getenv("IMAGE_ANALYSIS_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"image_analysis listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
