from fastapi import FastAPI, HTTPException

from app.providers.dummy import DummyModelProvider
from app.registry import ModelInfo, registry
from app.schemas import (
    ErrorEnvelope,
    ImageUrlPart,
    NormalizedOutputMessage,
    ResponseEnvelope,
    ResponseRequest,
    TextPart,
    Usage,
)

SERVICE_NAME = "llm"
SERVICE_VERSION = "0.1.0"

app = FastAPI(title="VANESSA LLM Service", version=SERVICE_VERSION)

if not registry.list_models():
    registry.register_provider(DummyModelProvider())


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


@app.get("/v1/models")
def list_models() -> list[dict[str, object]]:
    models: list[ModelInfo] = registry.list_models()
    return [
        {
            "id": model.id,
            "display_name": model.display_name,
            "capabilities": {
                "text": model.capabilities.text,
                "image_input": model.capabilities.image_input,
            },
            "status": model.status,
            "provider_type": model.provider_type,
        }
        for model in models
    ]


def _contains_image_parts(request: ResponseRequest) -> bool:
    return any(
        isinstance(part, ImageUrlPart)
        for message in request.input
        for part in message.content
    )


def _build_response(request: ResponseRequest) -> ResponseEnvelope:
    try:
        provider = registry.get_model(request.model)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorEnvelope(code="model_not_found", message=str(exc)).model_dump(),
        ) from exc

    if _contains_image_parts(request) and not provider.info.capabilities.image_input:
        raise HTTPException(
            status_code=422,
            detail=ErrorEnvelope(
                code="unsupported_input",
                message=f"Model '{request.model}' does not support image input.",
            ).model_dump(),
        )

    result = provider.generate(request)
    usage = Usage(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.prompt_tokens + result.completion_tokens,
    )
    return ResponseEnvelope(
        model=request.model,
        output=[
            NormalizedOutputMessage(
                role="assistant",
                content=[TextPart(type="text", text=result.output_text)],
            )
        ],
        usage=usage,
    )


@app.post("/v1/responses", response_model=ResponseEnvelope)
def create_response(request: ResponseRequest) -> ResponseEnvelope:
    return _build_response(request)


@app.post("/v1/chat/completions", response_model=ResponseEnvelope)
def create_chat_completion(request: ResponseRequest) -> ResponseEnvelope:
    return _build_response(request)
