from __future__ import annotations

import base64

from image_analysis.app import main as service


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _payload(*, tasks: list[str] | None = None) -> dict[str, object]:
    return {
        "image": {"data_base64": ONE_PIXEL_PNG, "mime_type": "image/png"},
        "tasks": tasks or ["license_plate_recognition"],
        "runtime": {
            "task_defaults": {
                "plate_detector": "plate-detector",
                "plate_ocr": "plate-ocr",
                "object_detector": "object-detector",
                "captioner": "captioner",
            }
        },
    }


def test_analyze_rejects_invalid_base64() -> None:
    payload = _payload()
    payload["image"] = {"data_base64": "not-base64", "mime_type": "image/png"}

    result, status = service._analyze(payload)

    assert status == 400
    assert result["error"] == "invalid_image"


def test_analyze_rejects_unknown_task() -> None:
    result, status = service._analyze(_payload(tasks=["unknown"]))

    assert status == 400
    assert result["error"] == "invalid_tasks"


def test_fake_mode_returns_plate_objects_and_caption(monkeypatch) -> None:
    monkeypatch.setenv("IMAGE_ANALYSIS_FAKE_MODE", "1")
    monkeypatch.setattr(service, "Image", None)

    result, status = service._analyze(_payload(tasks=["license_plate_recognition", "object_detection", "captioning"]))

    assert status == 200
    assert result["license_plates"][0]["text"] == "LOCAL123"
    assert result["license_plates"][0]["plate_detector_model_id"] == "plate-detector"
    assert result["objects"][0]["label"] == "vehicle"
    assert result["caption"]["text"]
    assert "warnings" not in result


def test_empty_detection_runtime_still_returns_requested_sections(monkeypatch) -> None:
    monkeypatch.delenv("IMAGE_ANALYSIS_FAKE_MODE", raising=False)
    monkeypatch.setattr(service, "Image", None)

    result, status = service._analyze(_payload(tasks=["license_plate_recognition", "object_detection"]))

    assert status == 200
    assert result["license_plates"] == []
    assert result["objects"] == []
    assert result["warnings"][0]["code"] == "image_runtime_unavailable"


def test_florence2_transformers_patch_adds_missing_forced_bos_token_id() -> None:
    class DummyPretrainedConfig:
        pass

    service._patch_florence2_transformers_config(DummyPretrainedConfig)

    assert DummyPretrainedConfig.forced_bos_token_id is None


def test_malformed_image_is_rejected_when_decoder_is_available(monkeypatch) -> None:
    class BrokenImage:
        @staticmethod
        def open(_source):
            raise ValueError("broken image")

    payload = _payload()
    payload["image"] = {
        "data_base64": base64.b64encode(b"not an image").decode("ascii"),
        "mime_type": "image/png",
    }
    monkeypatch.setattr(service, "Image", BrokenImage)

    result, status = service._analyze(payload)

    assert status == 400
    assert result["error"] == "invalid_image"
