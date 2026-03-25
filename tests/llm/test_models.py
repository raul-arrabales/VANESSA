from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_MAIN_PATH = PROJECT_ROOT / "llm" / "app" / "main.py"


def _load_list_models_fn():
    llm_root = PROJECT_ROOT / "llm"
    original_sys_path = list(sys.path)
    original_app_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    spec = importlib.util.spec_from_file_location("vanessa_llm_main", LLM_MAIN_PATH)
    assert spec is not None and spec.loader is not None
    try:
        sys.path.insert(0, str(llm_root))
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.list_models
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(original_app_modules)
        sys.path[:] = original_sys_path


def test_models_catalog_output_shape() -> None:
    list_models = _load_list_models_fn()
    payload = list_models()

    assert payload["object"] == "list"
    assert isinstance(payload["data"], list)
    assert payload["data"], "Expected at least one model entry"

    for model in payload["data"]:
        assert set(model.keys()) == {
            "id",
            "object",
            "owned_by",
            "display_name",
            "capabilities",
            "status",
            "provider_type",
            "provider_config_ref",
            "metadata",
        }
        assert model["object"] == "model"
        assert set(model["capabilities"].keys()) == {"text", "image_input", "embeddings"}
        assert isinstance(model["capabilities"]["text"], bool)
        assert isinstance(model["capabilities"]["image_input"], bool)
        assert isinstance(model["capabilities"]["embeddings"], bool)
        assert isinstance(model["metadata"], dict)


def test_models_catalog_includes_dummy_model() -> None:
    list_models = _load_list_models_fn()
    payload = list_models()

    dummy = next((model for model in payload["data"] if model["id"] == "dummy"), None)
    assert dummy is not None
    assert dummy["display_name"] == "Dummy Test Model"
    assert dummy["provider_type"] == "dummy"
    assert dummy["status"] == "available"
    assert dummy["capabilities"] == {"text": True, "image_input": False, "embeddings": False}


def test_models_catalog_includes_local_vllm_model() -> None:
    list_models = _load_list_models_fn()
    payload = list_models()
    local_default = next(
        (model for model in payload["data"] if model["id"] == "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"), None
    )
    assert local_default is not None
    assert local_default["provider_type"] == "local_vllm"
    assert local_default["capabilities"]["text"] is True


def test_models_catalog_includes_local_vllm_embeddings_model() -> None:
    list_models = _load_list_models_fn()
    payload = list_models()
    embeddings_model = next(
        (model for model in payload["data"] if model["id"] == "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"), None
    )
    assert embeddings_model is not None
    assert embeddings_model["provider_type"] == "local_vllm"
    assert embeddings_model["capabilities"]["embeddings"] is True
