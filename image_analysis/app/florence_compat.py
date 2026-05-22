from __future__ import annotations

from typing import Any


def patch_florence2_transformers_config(pretrained_config_cls: Any) -> None:
    if not hasattr(pretrained_config_cls, "forced_bos_token_id"):
        setattr(pretrained_config_cls, "forced_bos_token_id", None)


def patch_florence2_transformers_model(pretrained_model_cls: Any) -> None:
    for attribute in ("_supports_sdpa", "_supports_flash_attn_2"):
        try:
            getattr(pretrained_model_cls, attribute)
        except AttributeError:
            setattr(pretrained_model_cls, attribute, False)


def patch_florence2_transformers_tokenizer(tokenizer_base_cls: Any) -> None:
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


def patch_florence2_model_compat(model: Any) -> None:
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


def resize_caption_token_embeddings(model: Any, processor: Any) -> None:
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
