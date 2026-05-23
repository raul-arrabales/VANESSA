from __future__ import annotations

from typing import Any

import numpy as np

from ..payloads import decode_image_payload, encode_image, fake_mode

try:  # pragma: no cover - optional runtime dependency
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


def _coerce_xyxy(value: Any) -> list[int] | None:
    try:
        values = list(value)
    except TypeError:
        return None
    if len(values) < 4:
        return None
    try:
        x1, y1, x2, y2 = [int(round(float(values[index]))) for index in range(4)]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def _coerce_polygon(value: Any) -> list[list[float]] | None:
    if value is None:
        return None
    try:
        points = list(value)
    except TypeError:
        return None
    if len(points) != 4:
        return None
    polygon: list[list[float]] = []
    for point in points:
        try:
            x, y = list(point)[:2]
            polygon.append([float(x), float(y)])
        except (TypeError, ValueError):
            return None
    return polygon


def _box_from_item(item: Any) -> tuple[list[int] | None, list[list[float]] | None]:
    if isinstance(item, dict):
        polygon = _coerce_polygon(item.get("polygon") or item.get("points"))
        box = _coerce_xyxy(item.get("box_xyxy") or item.get("bbox") or item.get("box"))
        if box is None and polygon is not None:
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            box = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        return box, polygon
    return _coerce_xyxy(item), None


def _cover_plate(car: Any, x1: int, y1: int, x2: int, y2: int) -> None:
    region = car[y1:y2, x1:x2, :3]
    if region.size == 0:
        return
    if cv2 is not None:
        blurred = cv2.GaussianBlur(region, (0, 0), sigmaX=8)
        neutral = np.full_like(region, np.median(region.reshape(-1, 3), axis=0).astype(np.uint8))
        car[y1:y2, x1:x2, :3] = ((blurred.astype(np.float32) * 0.65) + (neutral.astype(np.float32) * 0.35)).astype(np.uint8)
    else:
        neutral = np.median(region.reshape(-1, 3), axis=0).astype(np.uint8)
        car[y1:y2, x1:x2, :3] = neutral


def _alpha_composite(target: Any, overlay: Any, x: int, y: int) -> None:
    height, width = overlay.shape[:2]
    if width <= 0 or height <= 0:
        return
    target_region = target[y : y + height, x : x + width]
    if overlay.shape[2] == 4:
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        target_region[:, :, :3] = (
            overlay[:, :, :3].astype(np.float32) * alpha + target_region[:, :, :3].astype(np.float32) * (1.0 - alpha)
        ).astype(np.uint8)
    else:
        target_region[:, :, :3] = overlay[:, :, :3]


def _place_rect(car: Any, logo: Any, box: list[int]) -> dict[str, Any]:
    image_height, image_width = car.shape[:2]
    x1, y1, x2, y2 = box
    x1 = max(0, min(image_width - 1, x1))
    x2 = max(1, min(image_width, x2))
    y1 = max(0, min(image_height - 1, y1))
    y2 = max(1, min(image_height, y2))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("plate box is outside the image")
    plate_width = x2 - x1
    plate_height = y2 - y1
    _cover_plate(car, x1, y1, x2, y2)
    scale = min(plate_width / max(1, logo.shape[1]), plate_height / max(1, logo.shape[0]))
    new_width = max(1, int(round(logo.shape[1] * scale)))
    new_height = max(1, int(round(logo.shape[0] * scale)))
    if cv2 is not None:
        resized = cv2.resize(logo, (new_width, new_height), interpolation=cv2.INTER_AREA)
    else:
        from PIL import Image

        resized = np.array(Image.fromarray(logo).resize((new_width, new_height)))
    offset_x = x1 + (plate_width - new_width) // 2
    offset_y = y1 + (plate_height - new_height) // 2
    _alpha_composite(car, resized, offset_x, offset_y)
    return {"box_xyxy": [x1, y1, x2, y2], "mode": "rect", "logo_box_xyxy": [offset_x, offset_y, offset_x + new_width, offset_y + new_height]}


def _place_polygon(car: Any, logo: Any, polygon: list[list[float]], box: list[int]) -> dict[str, Any]:
    if cv2 is None:
        placement = _place_rect(car, logo, box)
        placement["mode"] = "rect_fallback"
        return placement
    x1, y1, x2, y2 = box
    _cover_plate(car, max(0, x1), max(0, y1), min(car.shape[1], x2), min(car.shape[0], y2))
    source = np.float32([[0, 0], [logo.shape[1] - 1, 0], [logo.shape[1] - 1, logo.shape[0] - 1], [0, logo.shape[0] - 1]])
    destination = np.float32(polygon)
    matrix = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(logo, matrix, (car.shape[1], car.shape[0]))
    if warped.shape[2] == 4:
        alpha = warped[:, :, 3:4].astype(np.float32) / 255.0
        car[:, :, :3] = (warped[:, :, :3].astype(np.float32) * alpha + car[:, :, :3].astype(np.float32) * (1.0 - alpha)).astype(np.uint8)
    else:
        mask = np.any(warped[:, :, :3] > 0, axis=2, keepdims=True)
        car[:, :, :3] = np.where(mask, warped[:, :, :3], car[:, :, :3])
    return {"box_xyxy": box, "polygon": polygon, "mode": "polygon"}


def replace_plate_logos(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _car_raw, width, height, car_image, error = decode_image_payload(payload.get("car_image"), field_name="car_image")
    if error:
        raise ValueError(str(error.get("message") or error.get("error")))
    _logo_raw, _logo_width, _logo_height, logo_image, error = decode_image_payload(payload.get("logo_image"), field_name="logo_image")
    if error:
        raise ValueError(str(error.get("message") or error.get("error")))
    if car_image is None or logo_image is None:
        raise ValueError("Pillow is required for image generation payload decoding")

    car = np.array(car_image.convert("RGBA"))
    logo = np.array(logo_image.convert("RGBA"))
    plate_boxes = payload.get("plate_boxes")
    if not isinstance(plate_boxes, list) or not plate_boxes:
        raise ValueError("plate_boxes must be a non-empty array")

    placements: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for index, item in enumerate(plate_boxes):
        box, polygon = _box_from_item(item)
        if box is None:
            warnings.append({"code": "invalid_plate_box", "message": "Plate box could not be parsed", "index": index})
            continue
        try:
            placement = _place_polygon(car, logo, polygon, box) if polygon is not None else _place_rect(car, logo, box)
            placement["index"] = index
            placements.append(placement)
        except Exception as exc:
            warnings.append({"code": "plate_logo_placement_failed", "message": str(exc), "index": index})

    if fake_mode() and not placements:
        warnings.append({"code": "fake_plate_logo_noop", "message": "No plate boxes were replaced"})

    from PIL import Image

    output = Image.fromarray(car, mode="RGBA")
    encoded = encode_image(output, mime_type="image/png")
    encoded["width"] = width
    encoded["height"] = height
    return encoded, placements, warnings
