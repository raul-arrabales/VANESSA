from fastapi import FastAPI

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
