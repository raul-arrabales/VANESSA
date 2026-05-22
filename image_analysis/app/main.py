from __future__ import annotations

import base64
import gc
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:  # pragma: no cover - optional dependency in lightweight test environments
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]

SERVICE_VERSION = "0.1.0"
VALID_TASKS = {"license_plate_recognition", "object_detection", "captioning"}
DEFAULT_PORT = 8090
ROLE_GATEWAY = "gateway"
ROLE_ANPR = "anpr"
ROLE_OBJECTS = "objects"
ROLE_CAPTIONING = "captioning"
VALID_ROLES = {ROLE_GATEWAY, ROLE_ANPR, ROLE_OBJECTS, ROLE_CAPTIONING}
ROLE_TASKS = {
    ROLE_ANPR: {"license_plate_recognition"},
    ROLE_OBJECTS: {"object_detection"},
    ROLE_CAPTIONING: {"captioning"},
}
TASK_ROLE = {
    "license_plate_recognition": ROLE_ANPR,
    "object_detection": ROLE_OBJECTS,
    "captioning": ROLE_CAPTIONING,
}
_ALPR_PIPELINE: Any | None = None
_OBJECT_DETECTOR: Any | None = None
_CAPTIONER: tuple[Any, Any] | None = None
_MODEL_LOCK = threading.RLock()
DEFAULT_CAPTION_MODEL_ID = "florence-community/Florence-2-base-ft"

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


def _service_role() -> str:
    role = os.getenv("IMAGE_ANALYSIS_ROLE", ROLE_GATEWAY).strip().lower() or ROLE_GATEWAY
    return role if role in VALID_ROLES else ROLE_GATEWAY


def _keep_heavy_models_loaded() -> bool:
    return os.getenv("IMAGE_ANALYSIS_KEEP_HEAVY_MODELS_LOADED", "").strip().lower() in {"1", "true", "yes", "on"}


def _release_torch_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _release_object_detector() -> None:
    global _OBJECT_DETECTOR
    if _OBJECT_DETECTOR is not None:
        _OBJECT_DETECTOR = None
        _release_torch_memory()


def _release_captioner() -> None:
    global _CAPTIONER
    if _CAPTIONER is not None:
        _CAPTIONER = None
        _release_torch_memory()


def _prepare_heavy_model(task: str) -> None:
    if _keep_heavy_models_loaded():
        return
    if task == "object_detection":
        _release_captioner()
    elif task == "captioning":
        _release_object_detector()


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
            "id": _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID),
            "display_name": "Image captioner",
            "provider_resource_id": _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID),
            "metadata": {"task_key": "image_captioning", "engine": "florence-2"},
        },
    ]


def _resources_for_role(role: str) -> list[dict[str, Any]]:
    resources = _resources()
    if role == ROLE_GATEWAY:
        return resources
    task_keys_by_role = {
        ROLE_ANPR: {"image_plate_detection", "image_plate_ocr"},
        ROLE_OBJECTS: {"object_detection"},
        ROLE_CAPTIONING: {"image_captioning"},
    }
    task_keys = task_keys_by_role.get(role, set())
    return [resource for resource in resources if dict(resource.get("metadata") or {}).get("task_key") in task_keys]


def _worker_url(role: str) -> str:
    env_names = {
        ROLE_ANPR: "IMAGE_ANALYSIS_ANPR_URL",
        ROLE_OBJECTS: "IMAGE_ANALYSIS_OBJECTS_URL",
        ROLE_CAPTIONING: "IMAGE_ANALYSIS_CAPTIONING_URL",
    }
    defaults = {
        ROLE_ANPR: "http://image_analysis_anpr:8091",
        ROLE_OBJECTS: "http://image_analysis_objects:8092",
        ROLE_CAPTIONING: "http://image_analysis_captioning:8093",
    }
    env_name = env_names.get(role, "")
    default = defaults.get(role, "")
    return os.getenv(env_name, default).strip().rstrip("/") or default


def _worker_timeout(role: str) -> float:
    env_names = {
        ROLE_ANPR: "IMAGE_ANALYSIS_ANPR_TIMEOUT_SECONDS",
        ROLE_OBJECTS: "IMAGE_ANALYSIS_OBJECTS_TIMEOUT_SECONDS",
        ROLE_CAPTIONING: "IMAGE_ANALYSIS_CAPTIONING_TIMEOUT_SECONDS",
    }
    defaults = {
        ROLE_ANPR: 120.0,
        ROLE_OBJECTS: 180.0,
        ROLE_CAPTIONING: 300.0,
    }
    try:
        timeout = float(os.getenv(env_names.get(role, ""), str(defaults.get(role, 120.0))))
    except ValueError:
        timeout = defaults.get(role, 120.0)
    return timeout if timeout > 0 else defaults.get(role, 120.0)


def _gateway_health_worker_timeout() -> float:
    try:
        timeout = float(os.getenv("IMAGE_ANALYSIS_WORKER_HEALTH_TIMEOUT_SECONDS", "0.35"))
    except ValueError:
        timeout = 0.35
    return timeout if timeout > 0 else 0.35


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 5.0,
) -> tuple[dict[str, Any] | None, int, str | None]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310 - private compose URLs
            raw = response.read()
            if not raw:
                return {}, int(response.status), None
            parsed = json.loads(raw.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {}, int(response.status), None
    except HTTPError as exc:
        raw_error = exc.read()
        try:
            parsed_error = json.loads(raw_error.decode("utf-8")) if raw_error else {}
        except Exception:
            parsed_error = {}
        return parsed_error if isinstance(parsed_error, dict) else {}, int(exc.code), str(exc)
    except (OSError, TimeoutError, URLError) as exc:
        return None, 0, str(exc)
    except json.JSONDecodeError as exc:
        return None, 502, str(exc)


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


def _patch_florence2_transformers_model(pretrained_model_cls: Any) -> None:
    for attribute in ("_supports_sdpa", "_supports_flash_attn_2"):
        try:
            getattr(pretrained_model_cls, attribute)
        except AttributeError:
            setattr(pretrained_model_cls, attribute, False)


def _patch_florence2_transformers_tokenizer(tokenizer_base_cls: Any) -> None:
    try:
        getattr(tokenizer_base_cls, "additional_special_tokens")
        return
    except AttributeError:
        pass

    def additional_special_tokens(self: Any) -> list[str]:
        special_tokens_map = getattr(self, "special_tokens_map", {})
        tokens = special_tokens_map.get("additional_special_tokens", [])
        return list(tokens) if isinstance(tokens, list) else []

    setattr(tokenizer_base_cls, "additional_special_tokens", property(additional_special_tokens))


def _patch_florence2_model_compat(model: Any) -> None:
    language_model = getattr(model, "language_model", None)
    nested_model = getattr(language_model, "model", None) if language_model is not None else None
    for target in (model, language_model, nested_model):
        if target is None:
            continue
        for attribute in ("_supports_sdpa", "_supports_flash_attn_2"):
            try:
                getattr(target, attribute)
            except AttributeError:
                try:
                    setattr(target, attribute, False)
                except Exception:
                    pass


def _resize_caption_token_embeddings(model: Any, processor: Any) -> None:
    tokenizer = getattr(processor, "tokenizer", None)
    if tokenizer is None:
        return
    try:
        token_count = len(tokenizer)
    except Exception:
        return
    if token_count <= 0 or not hasattr(model, "resize_token_embeddings"):
        return
    try:
        input_embeddings = model.get_input_embeddings() if hasattr(model, "get_input_embeddings") else None
        current_count = getattr(input_embeddings, "num_embeddings", None)
    except Exception:
        current_count = None
    if current_count == token_count:
        return
    model.resize_token_embeddings(token_count)


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
        _prepare_heavy_model("object_detection")
        import torch
        from rfdetr import RFDETRBase, RFDETRLarge, RFDETRNano, RFDETRSmall

        variant = os.getenv("IMAGE_ANALYSIS_RFDETR_VARIANT", "nano").strip().lower()
        model_cls = {
            "base": RFDETRBase,
            "small": RFDETRSmall,
            "large": RFDETRLarge,
            "nano": RFDETRNano,
        }.get(variant, RFDETRNano)
        requested_device = os.getenv("IMAGE_ANALYSIS_RFDETR_DEVICE", "").strip().lower()
        device = requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
        _OBJECT_DETECTOR = model_cls(device=device)
    return _OBJECT_DETECTOR


def _object_results(image: Any, width: int, height: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    with _MODEL_LOCK:
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
        _prepare_heavy_model("captioning")
        import torch
        from transformers import AutoProcessor, Florence2ForConditionalGeneration, PreTrainedModel, PreTrainedTokenizerBase, PretrainedConfig

        _patch_florence2_transformers_config(PretrainedConfig)
        _patch_florence2_transformers_model(PreTrainedModel)
        _patch_florence2_transformers_tokenizer(PreTrainedTokenizerBase)

        model_id = _resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID)
        model = Florence2ForConditionalGeneration.from_pretrained(
            model_id,
            attn_implementation="eager",
            dtype=torch.float32,
        )
        _patch_florence2_model_compat(model)
        if hasattr(model, "config"):
            setattr(model.config, "use_cache", False)
        processor = AutoProcessor.from_pretrained(model_id)
        _resize_caption_token_embeddings(model, processor)
        model.eval()
        _CAPTIONER = (model, processor)
    return _CAPTIONER


def _model_tensor_context(model: Any) -> tuple[Any, Any]:
    try:
        parameter = next(model.parameters())
    except Exception:
        return None, None
    return getattr(parameter, "device", None), getattr(parameter, "dtype", None)


def _caption_image_size() -> int:
    try:
        return max(1, int(os.getenv("IMAGE_ANALYSIS_FLORENCE_IMAGE_SIZE", "512")))
    except ValueError:
        return 512


def _caption_max_tokens(payload: dict[str, Any]) -> int:
    try:
        default_tokens = int(os.getenv("IMAGE_ANALYSIS_FLORENCE_MAX_NEW_TOKENS", "48"))
    except ValueError:
        default_tokens = 48
    return _int_option(payload, "max_caption_tokens", max(1, default_tokens))


def _caption_num_beams() -> int:
    try:
        return max(1, int(os.getenv("IMAGE_ANALYSIS_FLORENCE_NUM_BEAMS", "1")))
    except ValueError:
        return 1


def _square_caption_image(image: Any) -> Any:
    size = getattr(image, "size", None)
    if not isinstance(size, tuple) or len(size) < 2 or Image is None:
        return image
    width, height = int(size[0]), int(size[1])
    if width <= 0 or height <= 0:
        return image
    side = max(width, height)
    canvas = image if width == height else Image.new("RGB", (side, side), (0, 0, 0))
    if canvas is not image:
        canvas.paste(image, ((side - width) // 2, (side - height) // 2))
    target_size = _caption_image_size()
    if side == target_size:
        return canvas
    resampling = getattr(getattr(Image, "Resampling", Image), "BICUBIC", 3)
    return canvas.resize((target_size, target_size), resample=resampling)


def _caption_result(image: Any, width: int, height: int, payload: dict[str, Any]) -> dict[str, Any]:
    import torch

    with _MODEL_LOCK:
        model, processor = _load_captioner()
        task_prompt = os.getenv("IMAGE_ANALYSIS_FLORENCE_CAPTION_PROMPT", "<CAPTION>")
        inputs = processor(text=task_prompt, images=_square_caption_image(image), return_tensors="pt")
        device, dtype = _model_tensor_context(model)
        if device is not None:
            inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
        if dtype is not None and "pixel_values" in inputs and hasattr(inputs["pixel_values"], "to"):
            inputs["pixel_values"] = inputs["pixel_values"].to(dtype=dtype)
        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=_caption_max_tokens(payload),
                num_beams=_caption_num_beams(),
                use_cache=False,
            )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(generated_text, task=task_prompt, image_size=(width, height))
    text = parsed.get(task_prompt, generated_text) if isinstance(parsed, dict) else generated_text
    return {"text": str(text).strip(), "captioner_model_id": _runtime_defaults(payload).get("captioner")}


def _empty_response(width: int, height: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "image": {"width": width, "height": height},
        "license_plates": [],
        "objects": [],
        "caption": None,
        "model_resources": _runtime_defaults(payload),
        "warnings": [],
    }


def _fake_analyze(payload: dict[str, Any], tasks: list[str], width: int, height: int) -> tuple[dict[str, Any], int]:
    response = _empty_response(width, height, payload)
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


def _analyze_local(payload: dict[str, Any], *, allowed_tasks: set[str] | None = None) -> tuple[dict[str, Any], int]:
    _raw, width, height, image, error = _decode_image(payload)
    if error:
        return error, 400
    tasks, error = _normalize_tasks(payload)
    if error:
        return error, 400
    if allowed_tasks is not None:
        invalid_tasks = sorted(set(tasks) - allowed_tasks)
        if invalid_tasks:
            return {"error": "invalid_tasks", "message": "task is not supported by this worker", "tasks": invalid_tasks}, 400

    response = _empty_response(width, height, payload)

    if _fake_mode():
        return _fake_analyze(payload, tasks, width, height)

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


def _worker_warning(role: str, *, status_code: int, message: str | None) -> dict[str, Any]:
    codes = {
        ROLE_ANPR: "plate_worker_unavailable",
        ROLE_OBJECTS: "object_worker_unavailable",
        ROLE_CAPTIONING: "caption_worker_unavailable",
    }
    default_messages = {
        ROLE_ANPR: "License plate worker is unavailable",
        ROLE_OBJECTS: "Object detection worker is unavailable",
        ROLE_CAPTIONING: "Image captioning worker is unavailable",
    }
    return {
        "code": codes.get(role, "image_worker_unavailable"),
        "message": message or default_messages.get(role, "Image analysis worker is unavailable"),
        "status_code": status_code,
    }


def _merge_worker_response(response: dict[str, Any], role: str, payload: dict[str, Any]) -> None:
    worker_image = payload.get("image") if isinstance(payload.get("image"), dict) else {}
    if response["image"].get("width", 0) <= 0 and isinstance(worker_image.get("width"), int):
        response["image"]["width"] = worker_image["width"]
    if response["image"].get("height", 0) <= 0 and isinstance(worker_image.get("height"), int):
        response["image"]["height"] = worker_image["height"]

    worker_warnings = payload.get("warnings")
    if isinstance(worker_warnings, list):
        response["warnings"].extend([item for item in worker_warnings if isinstance(item, dict)])

    if role == ROLE_ANPR:
        license_plates = payload.get("license_plates")
        response["license_plates"] = license_plates if isinstance(license_plates, list) else []
    elif role == ROLE_OBJECTS:
        objects = payload.get("objects")
        response["objects"] = objects if isinstance(objects, list) else []
    elif role == ROLE_CAPTIONING:
        caption = payload.get("caption")
        response["caption"] = caption if isinstance(caption, dict) else None


def _gateway_worker_analyze(role: str, payload: dict[str, Any], tasks: list[str]) -> tuple[dict[str, Any] | None, int, str | None]:
    worker_payload = {**payload, "tasks": tasks}
    return _http_json(
        _worker_url(role) + "/v1/analyze",
        method="POST",
        payload=worker_payload,
        timeout_seconds=_worker_timeout(role),
    )


def _analyze(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    _raw, width, height, image, error = _decode_image(payload)
    if error:
        return error, 400
    tasks, error = _normalize_tasks(payload)
    if error:
        return error, 400

    if _fake_mode():
        return _fake_analyze(payload, tasks, width, height)

    response = _empty_response(width, height, payload)
    if image is None:
        response["warnings"].append({"code": "image_runtime_unavailable", "message": "Pillow is unavailable in image_analysis gateway"})

    tasks_by_role: dict[str, list[str]] = {}
    for task in tasks:
        role = TASK_ROLE.get(task)
        if role:
            tasks_by_role.setdefault(role, []).append(task)

    for role, role_tasks in tasks_by_role.items():
        worker_payload, status_code, error_message = _gateway_worker_analyze(role, payload, role_tasks)
        if worker_payload is None or status_code < 200 or status_code >= 300:
            message = None
            if isinstance(worker_payload, dict):
                message = str(worker_payload.get("message") or worker_payload.get("error") or "").strip() or None
            response["warnings"].append(_worker_warning(role, status_code=status_code, message=message or error_message))
            continue
        _merge_worker_response(response, role, worker_payload)

    if not response["warnings"]:
        response.pop("warnings", None)
    return response, 200


def _analyze_for_role(payload: dict[str, Any], role: str) -> tuple[dict[str, Any], int]:
    if role == ROLE_GATEWAY:
        return _analyze(payload)
    return _analyze_local(payload, allowed_tasks=ROLE_TASKS.get(role, set()))


def _worker_health(role: str) -> dict[str, Any]:
    payload, status_code, error_message = _http_json(
        _worker_url(role) + "/health",
        timeout_seconds=_gateway_health_worker_timeout(),
    )
    return {
        "reachable": payload is not None and 200 <= status_code < 300,
        "status_code": status_code,
        "url": _worker_url(role),
        "message": error_message,
    }


def _health_for_role(role: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "service": "image_analysis" if role == ROLE_GATEWAY else f"image_analysis_{role}",
        "role": role,
        "version": SERVICE_VERSION,
        "fake_mode": _fake_mode(),
    }
    if role == ROLE_GATEWAY and not _fake_mode():
        payload["workers"] = {
            worker_role: _worker_health(worker_role)
            for worker_role in (ROLE_ANPR, ROLE_OBJECTS, ROLE_CAPTIONING)
        }
    if role != ROLE_GATEWAY:
        payload["tasks"] = sorted(ROLE_TASKS.get(role, set()))
    return payload


def _resources_from_worker(role: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload, status_code, error_message = _http_json(
        _worker_url(role) + "/v1/resources",
        timeout_seconds=_gateway_health_worker_timeout(),
    )
    if payload is None or status_code < 200 or status_code >= 300:
        return [], _worker_warning(role, status_code=status_code, message=error_message)
    raw_resources = payload.get("resources")
    if not isinstance(raw_resources, list):
        return [], _worker_warning(role, status_code=502, message="Worker resources payload is malformed")
    return [resource for resource in raw_resources if isinstance(resource, dict)], None


def _resources_payload_for_role(role: str) -> dict[str, Any]:
    if role != ROLE_GATEWAY or _fake_mode():
        return {"resources": _resources_for_role(role)}
    resources: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for worker_role in (ROLE_ANPR, ROLE_OBJECTS, ROLE_CAPTIONING):
        worker_resources, warning = _resources_from_worker(worker_role)
        resources.extend(worker_resources)
        if warning:
            warnings.append(warning)
    payload: dict[str, Any] = {"resources": resources}
    if warnings:
        payload["warnings"] = warnings
    return payload


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
        role = _service_role()
        if self.path == "/health":
            self._send_json(200, _health_for_role(role))
            return
        if self.path == "/v1/resources":
            self._send_json(200, _resources_payload_for_role(role))
            return
        self._send_json(404, {"error": "not_found", "message": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        role = _service_role()
        if self.path != "/v1/analyze":
            self._send_json(404, {"error": "not_found", "message": "Not found"})
            return
        payload = _read_json(self)
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return
        result, status = _analyze_for_role(payload, role)
        self._send_json(status, result)

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
