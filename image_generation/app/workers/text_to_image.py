from __future__ import annotations

import os
import threading
from typing import Any

from ..constants import DEFAULT_TEXT_TO_IMAGE_MODEL_ID
from ..payloads import encode_image, fake_generated_image, fake_mode, int_option, resource_id, runtime_defaults

_PIPELINE: Any | None = None
_PIPELINE_LOCK = threading.RLock()


def _device() -> str:
    return os.getenv("IMAGE_GENERATION_TEXT_TO_IMAGE_DEVICE", "cpu").strip().lower() or "cpu"


def _dtype_name() -> str:
    return os.getenv("IMAGE_GENERATION_TEXT_TO_IMAGE_DTYPE", "float32").strip().lower() or "float32"


def load_pipeline() -> Any:
    global _PIPELINE
    with _PIPELINE_LOCK:
        if _PIPELINE is None:
            import torch
            from diffusers import AutoPipelineForText2Image

            dtype = torch.float16 if _dtype_name() in {"float16", "fp16", "half"} else torch.float32
            model_id = resource_id("IMAGE_GENERATION_TEXT_TO_IMAGE_MODEL_ID", DEFAULT_TEXT_TO_IMAGE_MODEL_ID)
            _PIPELINE = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=dtype, use_safetensors=True)
            _PIPELINE = _PIPELINE.to(_device())
        return _PIPELINE


def text_to_image_result(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt is required for text_to_image")
    width = int_option(payload, "width", 256, minimum=64, maximum=1024)
    height = int_option(payload, "height", 256, minimum=64, maximum=1024)
    steps = int_option(payload, "num_inference_steps", 8, minimum=1, maximum=100)
    seed = int_option(payload, "seed", 0, minimum=0) if "seed" in (payload.get("options") or {}) or "seed" in payload else None
    negative_prompt = str(payload.get("negative_prompt") or "").strip() or None
    model_defaults = runtime_defaults(payload)

    if fake_mode():
        image = fake_generated_image(prompt, width=width, height=height)
    else:
        import torch

        generator = None
        if seed is not None:
            generator = torch.Generator(device=_device()).manual_seed(seed)
        pipeline = load_pipeline()
        image = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=generator,
        ).images[0]

    encoded = encode_image(image, mime_type="image/png")
    encoded["generator_model_id"] = model_defaults.get("generator")
    return encoded
