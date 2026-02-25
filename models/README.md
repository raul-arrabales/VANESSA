# Model Assets Layout

VANESSA supports local-first LLM serving through `llm_runtime` (vLLM).

## LLM Models

Store local LLM artifacts under:

`models/llm/<model-name>/...`

Example:

`models/llm/tinyllama/`

Set `LLM_LOCAL_MODEL_PATH` in compose env (`infra/.env.example` or your override) to the mounted runtime path used by vLLM, for example:

`LLM_LOCAL_MODEL_PATH=/models/llm/tinyllama`

## KWS Models

Wake-word model assets remain under:

`models/kws/`
