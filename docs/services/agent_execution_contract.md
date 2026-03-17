# Agent Execution Contract (Backend <-> Agent Engine)

## Internal Endpoints

- `POST /v1/internal/agent-executions`
- `GET /v1/internal/agent-executions/{id}`

## Required Headers

- `X-Service-Token`: shared service token (`AGENT_ENGINE_SERVICE_TOKEN`)
- `X-Request-Id`: request correlation id

## Create Execution Request

```json
{
  "agent_id": "agent.alpha",
  "input": {
    "prompt": "hello",
    "model": "optional-model-override",
    "retrieval": {
      "index": "knowledge_base",
      "query": "optional explicit retrieval query",
      "top_k": 5,
      "filters": {
        "tenant": "ops"
      }
    }
  },
  "requested_by_user_id": 123,
  "requested_by_role": "user",
  "runtime_profile": "offline",
  "platform_runtime": {
    "deployment_profile": {
      "id": "deployment-1",
      "slug": "local-default",
      "display_name": "Local Default"
    },
    "capabilities": {
      "llm_inference": {
        "id": "provider-1",
        "slug": "vllm-local-gateway",
        "provider_key": "vllm_local",
        "display_name": "vLLM local gateway",
        "description": "Current local-first LLM gateway",
        "adapter_kind": "openai_compatible_llm",
        "endpoint_url": "http://llm:8000",
        "healthcheck_url": "http://llm:8000/health",
        "enabled": true,
        "config": {
          "chat_completion_path": "/v1/chat/completions"
        },
        "binding_config": {}
      },
      "embeddings": {
        "id": "provider-embeddings",
        "slug": "vllm-embeddings-local",
        "provider_key": "vllm_embeddings_local",
        "display_name": "vLLM embeddings local",
        "description": "Primary embeddings endpoint",
        "adapter_kind": "openai_compatible_embeddings",
        "endpoint_url": "http://llm:8000",
        "healthcheck_url": "http://llm:8000/health",
        "enabled": true,
        "config": {
          "embeddings_path": "/v1/embeddings",
          "forced_model_id": "local-vllm-embeddings-default"
        },
        "binding_config": {}
      },
      "vector_store": {
        "id": "provider-2",
        "slug": "weaviate-local",
        "provider_key": "weaviate_local",
        "display_name": "Weaviate local",
        "description": "Primary Weaviate endpoint",
        "adapter_kind": "weaviate_http",
        "endpoint_url": "http://weaviate:8080",
        "healthcheck_url": "http://weaviate:8080/v1/.well-known/ready",
        "enabled": true,
        "config": {},
        "binding_config": {}
      }
    }
  },
  "org_id": "optional-org",
  "group_id": "optional-group"
}
```

## Canonical Execution Response

```json
{
  "execution": {
    "id": "execution-uuid",
    "status": "succeeded",
    "agent_ref": "agent.alpha",
    "agent_version": "v1",
    "model_ref": "model.default",
    "runtime_profile": "offline",
    "created_at": "2026-01-01T00:00:00+00:00",
    "started_at": "2026-01-01T00:00:00+00:00",
    "finished_at": "2026-01-01T00:00:01+00:00",
    "result": {
      "output_text": "Agent 'agent.alpha' executed in offline profile",
      "tool_calls": [],
      "embedding_calls": [],
      "retrieval_calls": [],
      "model_calls": [
        {
          "provider_slug": "vllm-local-gateway",
          "provider_key": "vllm_local",
          "deployment_profile_slug": "local-default",
          "requested_model": "model.default",
          "status_code": 200
        }
      ]
    },
    "error": null
  }
}
```

`platform_runtime` is execution-scoped and resolved by backend from the active platform bindings immediately before the internal engine call. Agent engine consumes this snapshot directly and does not query the backend control plane or platform tables itself.

`input.retrieval` is optional and execution-scoped. In v1 it is text-query only at the public API boundary, but agent engine now resolves the query through the active `embeddings` binding before querying the active `vector_store` binding. The active vector binding may currently resolve to either `weaviate_http` or `qdrant_http`.

`input.model` is optional and execution-scoped. When present, agent engine uses it as the requested LLM model instead of the agent spec default. Backend uses this for product-facing knowledge chat after resolving the user-selected model through model governance.

## Error Codes

- `EXEC_POLICY_DENIED`
- `EXEC_RUNTIME_PROFILE_BLOCKED`
- `EXEC_AGENT_NOT_FOUND`
- `EXEC_AGENT_VERSION_NOT_FOUND`
- `EXEC_MODEL_NOT_ALLOWED`
- `EXEC_TOOL_NOT_ALLOWED`
- `EXEC_TIMEOUT`
- `EXEC_UPSTREAM_UNAVAILABLE`
- `EXEC_INTERNAL_ERROR`

## Fallback Behavior (`AGENT_EXECUTION_FALLBACK`)

When backend execution fallback is enabled (`AGENT_EXECUTION_FALLBACK=true`), backend still does not execute agents locally.
Fallback applies only to engine transport failures (for example unreachable service or timeout).

Response:

- Status: `503`
- Payload:

```json
{
  "error": "EXEC_UPSTREAM_UNAVAILABLE",
  "message": "Agent execution service is temporarily unavailable",
  "details": {
    "operation": "create_execution",
    "fallback_applied": true,
    "request_id": "request-id"
  }
}
```

`operation` is `create_execution` for `POST /v1/agent-executions` and `get_execution` for `GET /v1/agent-executions/{id}`.
