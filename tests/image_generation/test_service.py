from __future__ import annotations

import base64
from io import BytesIO

from image_generation.app import gateway
from image_generation.app import resources as image_resources
from image_generation.app import runtime
from image_generation.app.constants import ROLE_PLATE_LOGO, ROLE_TEXT_TO_IMAGE

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _image_payload(width: int = 20, height: int = 12, color: tuple[int, int, int, int] = (200, 200, 200, 255)) -> dict[str, str]:
    assert Image is not None
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return {"data_base64": base64.b64encode(output.getvalue()).decode("ascii"), "mime_type": "image/png"}


def _payload(*, tasks: list[str] | None = None) -> dict[str, object]:
    return {
        "tasks": tasks or ["text_to_image"],
        "prompt": "a small local test image",
        "runtime": {
            "task_defaults": {
                "generator": "generator-model",
                "plate_logo_processor": "plate-logo-processor-opencv",
            }
        },
    }


def test_generate_rejects_unknown_task() -> None:
    result, status = gateway.generate(_payload(tasks=["unknown"]))

    assert status == 400
    assert result["error"] == "invalid_tasks"


def test_fake_mode_returns_text_to_image(monkeypatch) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_FAKE_MODE", "1")

    result, status = gateway.generate(_payload(tasks=["text_to_image"]))

    assert status == 200
    assert result["image"]["mime_type"] == "image/png"
    assert result["image"]["generator_model_id"] == "generator-model"
    assert result["image"]["data_base64"]
    assert "warnings" not in result


def test_gateway_routes_requested_tasks_and_aggregates_worker_results(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def worker(role: str, payload: dict[str, object], tasks: list[str]):
        calls.append((role, tasks))
        if role == ROLE_TEXT_TO_IMAGE:
            return {"image": {"mime_type": "image/png", "data_base64": "abc", "width": 1, "height": 1}}, 200, None
        return {"image": {"mime_type": "image/png", "data_base64": "xyz", "width": 2, "height": 2}, "placements": [{"index": 0}]}, 200, None

    monkeypatch.delenv("IMAGE_GENERATION_FAKE_MODE", raising=False)
    monkeypatch.setattr(gateway, "gateway_worker_generate", worker)

    result, status = gateway.generate(_payload(tasks=["text_to_image", "license_plate_logo_replacement"]))

    assert status == 200
    assert calls == [
        (ROLE_TEXT_TO_IMAGE, ["text_to_image"]),
        (ROLE_PLATE_LOGO, ["license_plate_logo_replacement"]),
    ]
    assert result["image"]["data_base64"] == "xyz"
    assert result["placements"] == [{"index": 0}]


def test_gateway_rejects_disabled_worker_task(monkeypatch) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_WORKERS", "text_to_image")
    monkeypatch.setenv("IMAGE_GENERATION_FAKE_MODE", "1")

    result, status = gateway.generate(_payload(tasks=["license_plate_logo_replacement"]))

    assert status == 409
    assert result["error"] == "image_generation_task_disabled"
    assert result["tasks"] == ["license_plate_logo_replacement"]


def test_gateway_resources_only_include_enabled_workers(monkeypatch) -> None:
    calls: list[str] = []

    def resources(role: str):
        calls.append(role)
        return image_resources.resources_for_role(role), None

    monkeypatch.setenv("IMAGE_GENERATION_WORKERS", "plate_logo")
    monkeypatch.delenv("IMAGE_GENERATION_FAKE_MODE", raising=False)
    monkeypatch.setattr(gateway, "resources_from_worker", resources)

    payload = gateway.resources_payload_for_role("gateway")

    assert calls == [ROLE_PLATE_LOGO]
    assert {resource["metadata"]["task_key"] for resource in payload["resources"]} == {"image_plate_logo_replacement"}


def test_worker_rejects_unsupported_task() -> None:
    result, status = runtime.generate_for_role(_payload(tasks=["text_to_image"]), ROLE_PLATE_LOGO)

    assert status == 400
    assert result["error"] == "invalid_tasks"


def test_plate_logo_replacement_rect_preserves_dimensions(monkeypatch) -> None:
    if Image is None:
        return
    monkeypatch.delenv("IMAGE_GENERATION_FAKE_MODE", raising=False)
    payload = {
        "tasks": ["license_plate_logo_replacement"],
        "car_image": _image_payload(40, 24, (120, 120, 120, 255)),
        "logo_image": _image_payload(16, 8, (255, 0, 0, 180)),
        "plate_boxes": [{"box_xyxy": [10, 8, 30, 16]}],
        "runtime": {"task_defaults": {"plate_logo_processor": "plate-logo-processor-opencv"}},
    }

    result, status = runtime.generate_for_role(payload, ROLE_PLATE_LOGO)

    assert status == 200
    assert result["image"]["width"] == 40
    assert result["image"]["height"] == 24
    assert result["placements"][0]["mode"] == "rect"
    assert result["image"]["data_base64"] != payload["car_image"]["data_base64"]
