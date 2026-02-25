from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_PATH = PROJECT_ROOT / "llm"
if str(LLM_PATH) not in sys.path:
    sys.path.insert(0, str(LLM_PATH))

from app.main import create_chat_completion, create_response  # noqa: E402
from app.schemas import ResponseRequest  # noqa: E402


def test_unknown_model_returns_not_found() -> None:
    request = ResponseRequest(
        model="missing-model",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
    )

    with pytest.raises(HTTPException) as exc:
        create_response(request)

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "model_not_found"


def test_dummy_model_returns_deterministic_response() -> None:
    request = ResponseRequest(
        model="dummy",
        temperature=0,
        max_tokens=12,
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    )

    response = create_chat_completion(request)

    assert response.model == "dummy"
    assert response.error is None
    assert response.output[0].content[0].text == "Hello, this is the test dummy model."
    assert response.usage.total_tokens == (
        response.usage.prompt_tokens + response.usage.completion_tokens
    )


def test_multimodal_payload_validation_rejects_unsupported_image_input() -> None:
    request = ResponseRequest(
        model="dummy",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "b64_json": "iVBORw0KGgoAAAANSUhEUgAA",
                        },
                    },
                ],
            }
        ],
    )

    with pytest.raises(HTTPException) as exc:
        create_response(request)

    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "unsupported_input"


def test_multimodal_payload_validation_rejects_invalid_image_part() -> None:
    with pytest.raises(ValidationError):
        ResponseRequest(
            model="dummy",
            input=[
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {}}],
                }
            ],
        )
