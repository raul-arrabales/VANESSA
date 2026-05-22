from __future__ import annotations

import os
import threading
from typing import Any

from ..constants import DEFAULT_CAPTION_MODEL_ID
from ..florence_compat import (
    patch_florence2_model_compat,
    patch_florence2_transformers_config,
    patch_florence2_transformers_model,
    patch_florence2_transformers_tokenizer,
    resize_caption_token_embeddings,
)
from ..payloads import Image, int_option, resource_id, runtime_defaults

_CAPTIONER: tuple[Any, Any] | None = None
_CAPTION_LOCK = threading.RLock()


def load_captioner() -> tuple[Any, Any]:
    global _CAPTIONER
    if _CAPTIONER is None:
        import torch
        from transformers import AutoProcessor, Florence2ForConditionalGeneration, PreTrainedModel, PreTrainedTokenizerBase, PretrainedConfig

        patch_florence2_transformers_config(PretrainedConfig)
        patch_florence2_transformers_model(PreTrainedModel)
        patch_florence2_transformers_tokenizer(PreTrainedTokenizerBase)

        model_id = resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID)
        model = Florence2ForConditionalGeneration.from_pretrained(
            model_id,
            attn_implementation="eager",
            dtype=torch.float32,
        )
        patch_florence2_model_compat(model)
        if hasattr(model, "config"):
            setattr(model.config, "use_cache", False)
        processor = AutoProcessor.from_pretrained(model_id)
        resize_caption_token_embeddings(model, processor)
        model.eval()
        _CAPTIONER = (model, processor)
    return _CAPTIONER


def model_tensor_context(model: Any) -> tuple[Any, Any]:
    try:
        parameter = next(model.parameters())
    except Exception:
        return None, None
    return getattr(parameter, "device", None), getattr(parameter, "dtype", None)


def caption_image_size() -> int:
    try:
        return max(1, int(os.getenv("IMAGE_ANALYSIS_FLORENCE_IMAGE_SIZE", "512")))
    except ValueError:
        return 512


def caption_max_tokens(payload: dict[str, Any]) -> int:
    try:
        default_tokens = int(os.getenv("IMAGE_ANALYSIS_FLORENCE_MAX_NEW_TOKENS", "48"))
    except ValueError:
        default_tokens = 48
    return int_option(payload, "max_caption_tokens", max(1, default_tokens))


def caption_num_beams() -> int:
    try:
        return max(1, int(os.getenv("IMAGE_ANALYSIS_FLORENCE_NUM_BEAMS", "1")))
    except ValueError:
        return 1


def square_caption_image(image: Any) -> Any:
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
    target_size = caption_image_size()
    if side == target_size:
        return canvas
    resampling = getattr(getattr(Image, "Resampling", Image), "BICUBIC", 3)
    return canvas.resize((target_size, target_size), resample=resampling)


def caption_result(image: Any, width: int, height: int, payload: dict[str, Any]) -> dict[str, Any]:
    import torch

    with _CAPTION_LOCK:
        model, processor = load_captioner()
        task_prompt = os.getenv("IMAGE_ANALYSIS_FLORENCE_CAPTION_PROMPT", "<CAPTION>")
        inputs = processor(text=task_prompt, images=square_caption_image(image), return_tensors="pt")
        device, dtype = model_tensor_context(model)
        if device is not None:
            inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
        if dtype is not None and "pixel_values" in inputs and hasattr(inputs["pixel_values"], "to"):
            inputs["pixel_values"] = inputs["pixel_values"].to(dtype=dtype)
        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=caption_max_tokens(payload),
                num_beams=caption_num_beams(),
                use_cache=False,
            )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(generated_text, task=task_prompt, image_size=(width, height))
    text = parsed.get(task_prompt, generated_text) if isinstance(parsed, dict) else generated_text
    return {"text": str(text).strip(), "captioner_model_id": runtime_defaults(payload).get("captioner")}
