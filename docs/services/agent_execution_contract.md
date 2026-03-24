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
        "resources": [
          {
            "id": "model.alpha",
            "resource_kind": "model",
            "ref_type": "managed_model",
            "managed_model_id": "model.alpha",
            "provider_resource_id": "model.alpha",
            "display_name": "Model Alpha"
          },
          {
            "id": "model.default",
            "resource_kind": "model",
            "ref_type": "managed_model",
            "managed_model_id": "model.default",
            "provider_resource_id": "model.default",
            "display_name": "Default Model"
          }
        ],
        "default_resource_id": "model.default",
        "default_resource": {
          "id": "model.default",
          "resource_kind": "model",
          "ref_type": "managed_model",
          "managed_model_id": "model.default",
          "provider_resource_id": "model.default",
          "display_name": "Default Model"
        },
        "resource_policy": {},
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
          "embeddings_path": "/v1/embeddings"
        },
        "resources": [
          {
            "id": "local-vllm-embeddings-default",
            "resource_kind": "model",
            "ref_type": "managed_model",
            "managed_model_id": "local-vllm-embeddings-default",
            "provider_resource_id": "local-vllm-embeddings-default",
            "display_name": "Local Embeddings Default"
          }
        ],
        "default_resource_id": "local-vllm-embeddings-default",
        "default_resource": {
          "id": "local-vllm-embeddings-default",
          "resource_kind": "model",
          "ref_type": "managed_model",
          "managed_model_id": "local-vllm-embeddings-default",
          "provider_resource_id": "local-vllm-embeddings-default",
          "display_name": "Local Embeddings Default"
        },
        "resource_policy": {},
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
        "resources": [],
        "default_resource_id": null,
        "default_resource": null,
        "resource_policy": {},
        "binding_config": {}
      },
      "mcp_runtime": {
        "id": "provider-mcp",
        "slug": "mcp-gateway-local",
        "provider_key": "mcp_gateway_local",
        "display_name": "MCP gateway local",
        "description": "Optional MCP runtime gateway",
        "adapter_kind": "mcp_http",
        "endpoint_url": "http://mcp_gateway:8080",
        "healthcheck_url": "http://mcp_gateway:8080/health",
        "enabled": true,
        "config": {},
        "resources": [],
        "default_resource_id": null,
        "default_resource": null,
        "resource_policy": {},
        "binding_config": {}
      },
      "sandbox_execution": {
        "id": "provider-sandbox",
        "slug": "sandbox-local",
        "provider_key": "sandbox_local",
        "display_name": "Sandbox local",
        "description": "Optional sandbox execution runtime",
        "adapter_kind": "sandbox_http",
        "endpoint_url": "http://sandbox:8000",
        "healthcheck_url": "http://sandbox:8000/health",
        "enabled": true,
        "config": {},
        "resources": [],
        "default_resource_id": null,
        "default_resource": null,
        "resource_policy": {},
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
      "output_text": "Here is the final answer after using a tool.",
      "tool_calls": [
        {
          "tool_ref": "tool.python_exec",
          "tool_name": "python_exec",
          "transport": "sandbox_http",
          "runtime_capability": "sandbox_execution",
          "provider_slug": "sandbox-local",
          "provider_key": "sandbox_local",
          "deployment_profile_slug": "local-default",
          "status_code": 200,
          "arguments": {
            "code": "print(2 + 2)"
          },
          "result": {
            "stdout": "4\n",
            "stderr": "",
            "result": null,
            "error": null
          }
        }
      ],
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

For resource-bearing capabilities, the runtime snapshot is authoritative:

- `llm_inference.resources` is the allow-list of managed model resources that may execute through the active binding.
- `llm_inference.default_resource_id` is used when `input.model` is omitted.
- `embeddings.default_resource_id` is the embeddings resource used for retrieval and vector ingestion.
- `vector_store.resource_policy` governs whether vector indexes must be explicitly bound or may be created/resolved under a deployment namespace.
- Agent engine resolves the selected managed model resource to the provider-facing model id before issuing upstream requests.

`input.retrieval` is optional and execution-scoped. In v1 it is text-query only at the public API boundary, but agent engine now resolves the query through the active `embeddings` binding before querying the active `vector_store` binding. The active vector binding may currently resolve to either `weaviate_http` or `qdrant_http`.

`input.model` is optional and execution-scoped. When present, agent engine treats it as a managed model id and requires that it be present in `platform_runtime.capabilities.llm_inference.resources`. When omitted, the active binding default resource is used. Backend uses this for product-facing knowledge chat after resolving the user-selected model through model governance.

Tool execution is also execution-scoped. Backend may include optional `mcp_runtime` and `sandbox_execution` capability bindings in `platform_runtime`. Agent engine uses those bindings only when the resolved agent tool catalog requires them. In the current convergence phase:

- `tool.web_search` uses `transport: mcp` and requires `platform_runtime.capabilities.mcp_runtime`
- `tool.python_exec` uses `transport: sandbox_http` and requires `platform_runtime.capabilities.sandbox_execution`

Tool loops are LLM-driven and bounded to three rounds.

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
