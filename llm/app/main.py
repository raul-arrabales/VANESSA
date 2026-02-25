from fastapi import FastAPI

from app.registry import ModelInfo, registry

SERVICE_NAME = "llm"
SERVICE_VERSION = "0.1.0"

app = FastAPI(title="VANESSA LLM Service", version=SERVICE_VERSION)


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
