from __future__ import annotations

import os
import threading
from typing import Any

from ..constants import COCO_LABELS
from ..payloads import as_box_xyxy, as_float, float_option, int_option, normalized_box, runtime_defaults

_OBJECT_DETECTOR: Any | None = None
_OBJECT_LOCK = threading.RLock()


def load_object_detector() -> Any:
    global _OBJECT_DETECTOR
    if _OBJECT_DETECTOR is None:
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


def object_results(image: Any, width: int, height: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    with _OBJECT_LOCK:
        detector = load_object_detector()
        threshold = float_option(payload, "object_detection", 0.25)
        max_results = int_option(payload, "max_objects", 50)
        model_defaults = runtime_defaults(payload)
        raw = detector.predict(image, threshold=threshold)
    xyxy = getattr(raw, "xyxy", [])
    confidences = getattr(raw, "confidence", getattr(raw, "confidences", []))
    class_ids = getattr(raw, "class_id", getattr(raw, "class_ids", []))
    results: list[dict[str, Any]] = []
    for box_value, confidence_value, class_id_value in zip(xyxy, confidences, class_ids, strict=False):
        confidence = as_float(confidence_value)
        if confidence < threshold:
            continue
        box = as_box_xyxy(box_value)
        if box is None:
            continue
        class_index = int(class_id_value)
        label = COCO_LABELS[class_index] if 0 <= class_index < len(COCO_LABELS) else str(class_index)
        results.append(
            {
                "label": label,
                "confidence": confidence,
                "box_xyxy": box,
                "box_normalized_xyxy": normalized_box(box, width, height),
                "object_detector_model_id": model_defaults.get("object_detector"),
            }
        )
        if len(results) >= max_results:
            break
    return results
