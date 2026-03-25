from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import load_runtime_controller_config
from .controller import RuntimeController

SERVICE_VERSION = "0.1.0"


class LoadModelRequest(BaseModel):
    runtime_model_id: str = Field(min_length=1)
    local_path: str = Field(min_length=1)
    managed_model_id: str | None = None
    display_name: str | None = None


config = load_runtime_controller_config()
controller = RuntimeController(config)
app = FastAPI(title=f"VANESSA {config.service_name}", version=SERVICE_VERSION)


def _capabilities_payload() -> dict[str, bool]:
    if config.capability == "embeddings":
        return {"text": False, "image_input": False, "embeddings": True}
    return {"text": True, "image_input": False, "embeddings": False}


def _child_request(
    path: str,
    *,
    method: str,
    body: bytes | None = None,
    stream: bool = False,
) -> Any:
    url = controller.child_base_url().rstrip("/") + path
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method.upper())
    if stream:
        return urlopen(request, timeout=60)
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
            return raw, int(response.status), response.headers.get("Content-Type", "application/json")
    except HTTPError as exc:
        return exc.read(), int(exc.code), exc.headers.get("Content-Type", "application/json")
    except URLError as exc:
        raise HTTPException(status_code=502, detail={"code": "runtime_unavailable", "message": str(exc.reason)}) from exc


def _loaded_state_or_409() -> dict[str, Any]:
    state = controller.get_state()
    if state["load_state"] != "loaded":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "runtime_model_not_loaded",
                "message": "Local runtime does not currently have a model loaded.",
                "runtime_state": state,
            },
        )
    return state


@app.on_event("startup")
def startup() -> None:
    controller.startup()


@app.on_event("shutdown")
def shutdown() -> None:
    controller.shutdown()


@app.get("/health")
def health() -> dict[str, Any]:
    state = controller.get_state()
    return {
        "status": "ok",
        "service": config.service_name,
        "version": SERVICE_VERSION,
        "runtime_state": state,
    }


@app.get("/v1/admin/runtime-state")
def runtime_state() -> dict[str, Any]:
    return controller.get_state()


@app.post("/v1/admin/load-model")
def load_model(payload: LoadModelRequest) -> dict[str, Any]:
    try:
        return controller.load_model(
            runtime_model_id=payload.runtime_model_id,
            local_path=payload.local_path,
            managed_model_id=payload.managed_model_id,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_runtime_model", "message": str(exc)},
        ) from exc


@app.post("/v1/admin/unload-model")
def unload_model() -> dict[str, Any]:
    return controller.unload_model()


@app.get("/v1/models")
def list_models() -> dict[str, object]:
    state = controller.get_state()
    if state["load_state"] != "loaded" or not state["runtime_model_id"]:
        return {"object": "list", "data": []}
    display_name = state["display_name"] or state["runtime_model_id"]
    return {
        "object": "list",
        "data": [
            {
                "id": state["runtime_model_id"],
                "object": "model",
                "owned_by": config.service_name,
                "display_name": display_name,
                "capabilities": _capabilities_payload(),
                "status": state["load_state"],
                "provider_type": "local_vllm_runtime",
                "provider_config_ref": f"{config.capability}/runtime",
                "metadata": {
                    "upstream_model": state["runtime_model_id"],
                    "local_path": state["local_path"],
                    "managed_model_id": state["managed_model_id"],
                },
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: FastAPIRequest):
    state = _loaded_state_or_409()
    if config.capability != "llm_inference":
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_input", "message": "This runtime only supports embeddings."},
        )
    body = await request.body()
    parsed = json.loads(body.decode("utf-8")) if body else {}
    if bool(parsed.get("stream")):
        upstream = _child_request("/v1/chat/completions", method="POST", body=body, stream=True)

        def _iter_chunks():
            with upstream as response:
                while True:
                    chunk = response.readline()
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            _iter_chunks(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    raw, status_code, content_type = _child_request("/v1/chat/completions", method="POST", body=body)
    return JSONResponse(content=json.loads(raw.decode("utf-8") or "{}"), status_code=status_code, media_type=content_type)


@app.post("/v1/embeddings")
async def embeddings(request: FastAPIRequest):
    _loaded_state_or_409()
    if config.capability != "embeddings":
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_input", "message": "This runtime only supports text inference."},
        )
    body = await request.body()
    raw, status_code, content_type = _child_request("/v1/embeddings", method="POST", body=body)
    return JSONResponse(content=json.loads(raw.decode("utf-8") or "{}"), status_code=status_code, media_type=content_type)
