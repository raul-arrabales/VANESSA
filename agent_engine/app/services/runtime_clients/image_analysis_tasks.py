from __future__ import annotations

IMAGE_ANALYSIS_DEFAULTS_BY_TASK = {
    "license_plate_recognition": ("plate_detector", "plate_ocr"),
    "object_detection": ("object_detector",),
    "captioning": ("captioner",),
}
