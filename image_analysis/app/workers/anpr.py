from __future__ import annotations

from typing import Any

from ..payloads import as_box_xyxy, as_float, float_option, int_option, normalized_box, resource_id, runtime_defaults

_ALPR_PIPELINE: Any | None = None


def load_alpr() -> Any:
    global _ALPR_PIPELINE
    if _ALPR_PIPELINE is None:
        from fast_alpr import ALPR

        _ALPR_PIPELINE = ALPR(
            detector_model=resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            ocr_model=resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
        )
    return _ALPR_PIPELINE


def plate_results(image: Any, width: int, height: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    import numpy as np

    detector_threshold = float_option(payload, "plate_detector", 0.25)
    max_results = int_option(payload, "max_license_plates", 20)
    model_defaults = runtime_defaults(payload)
    pipeline = load_alpr()
    frame_bgr = np.array(image)[:, :, ::-1]
    raw_results = pipeline.predict(frame_bgr)
    results: list[dict[str, Any]] = []
    for item in raw_results or []:
        detection = getattr(item, "detection", item)
        ocr = getattr(item, "ocr", None)
        confidence = as_float(getattr(detection, "confidence", None), as_float(getattr(item, "confidence", None), 0.0))
        if confidence < detector_threshold:
            continue
        box = as_box_xyxy(getattr(detection, "bounding_box", None) or getattr(detection, "box", None) or getattr(item, "box", None))
        if box is None:
            continue
        text = str(getattr(ocr, "text", None) or getattr(item, "text", "") or "").strip()
        text_confidence = as_float(getattr(ocr, "confidence", None), as_float(getattr(item, "text_confidence", None), 0.0))
        results.append(
            {
                "text": text,
                "text_confidence": text_confidence,
                "box_xyxy": box,
                "box_normalized_xyxy": normalized_box(box, width, height),
                "polygon": getattr(detection, "polygon", None),
                "plate_detector_model_id": model_defaults.get("plate_detector"),
                "plate_ocr_model_id": model_defaults.get("plate_ocr"),
            }
        )
        if len(results) >= max_results:
            break
    return results
