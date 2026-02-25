from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_PATH = PROJECT_ROOT / "llm"
if str(LLM_PATH) not in sys.path:
    sys.path.insert(0, str(LLM_PATH))

from app.main import list_models  # noqa: E402


def test_models_catalog_output_shape() -> None:
    payload = list_models()

    assert isinstance(payload, list)
    assert payload, "Expected at least one model entry"

    for model in payload:
        assert set(model.keys()) == {
            "id",
            "display_name",
            "capabilities",
            "status",
            "provider_type",
        }
        assert set(model["capabilities"].keys()) == {"text", "image_input"}
        assert isinstance(model["capabilities"]["text"], bool)
        assert isinstance(model["capabilities"]["image_input"], bool)


def test_models_catalog_includes_dummy_model() -> None:
    payload = list_models()

    dummy = next((model for model in payload if model["id"] == "dummy"), None)
    assert dummy is not None
    assert dummy["display_name"] == "Dummy Test Model"
    assert dummy["provider_type"] == "dummy"
    assert dummy["status"] == "available"
    assert dummy["capabilities"] == {"text": True, "image_input": False}
