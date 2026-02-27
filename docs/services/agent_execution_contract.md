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
    "prompt": "hello"
  },
  "requested_by_user_id": 123,
  "requested_by_role": "user",
  "runtime_profile": "offline",
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
      "model_calls": []
    },
    "error": null
  }
}
```

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

