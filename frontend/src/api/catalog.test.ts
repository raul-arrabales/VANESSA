import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createCatalogAgent,
  createCatalogTool,
  listCatalogAgents,
  listCatalogTools,
  previewCatalogAgentPrompt,
  testCatalogTool,
  updateCatalogAgent,
  updateCatalogTool,
  validateCatalogAgent,
  validateCatalogTool,
} from "./catalog";

describe("catalog api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists agents and tools with auth headers", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => String(input).endsWith("/agents") ? JSON.stringify({ agents: [] }) : JSON.stringify({ tools: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listCatalogAgents("token");
    await listCatalogTools("token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/catalog/agents",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/catalog/tools",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  it("supports create, update, validate, and test mutations", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.includes("/validate")) {
          if (url.includes("/agents/")) {
            return JSON.stringify({
              agent: { id: "agent.alpha", entity: { id: "agent.alpha", type: "agent", owner_user_id: 1, visibility: "private" }, current_version: "v1", status: "draft", published: false, published_at: null, spec: {} },
              validation: { valid: true, errors: [], warnings: [], resolved_tools: [], derived_runtime_requirements: { internet_required: false, sandbox_required: false } },
            });
          }
          return JSON.stringify({
            tool: { id: "tool.web_search", entity: { id: "tool.web_search", type: "tool", owner_user_id: 1, visibility: "private" }, current_version: "v1", status: "draft", published: false, published_at: null, spec: {} },
            validation: { valid: true, errors: [], warnings: [], runtime_checks: {} },
          });
        }
        if (url.includes("/test")) {
          return JSON.stringify({
            tool: { id: "tool.web_search", entity: { id: "tool.web_search", type: "tool", owner_user_id: 1, visibility: "private" }, current_version: "v1", status: "draft", published: false, published_at: null, spec: {} },
            execution: { input: { query: "OpenAI" }, request_metadata: {}, status_code: 200, ok: true, result: { results: [] } },
          });
        }
        if (url.includes("/prompt-preview")) {
          return JSON.stringify({
            prompt_preview: { messages: [], text: "preview" },
          });
        }
        if (url.includes("/agents")) {
          return JSON.stringify({
            agent: { id: "agent.alpha", entity: { id: "agent.alpha", type: "agent", owner_user_id: 1, visibility: "private" }, current_version: "v1", status: "draft", published: false, published_at: null, spec: {} },
          });
        }
        return JSON.stringify({
          tool: { id: "tool.web_search", entity: { id: "tool.web_search", type: "tool", owner_user_id: 1, visibility: "private" }, current_version: "v1", status: "draft", published: false, published_at: null, spec: {} },
        });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await createCatalogAgent(
      {
        id: "agent.alpha",
        publish: false,
        name: "Agent Alpha",
        description: "desc",
        instructions: "be concise",
        runtime_prompts: { retrieval_context: "Use retrieved context." },
        default_model_ref: null,
        tool_refs: [],
        runtime_constraints: { internet_required: false, sandbox_required: false },
      },
      "token",
    );
    await updateCatalogAgent(
      "agent.alpha",
      {
        publish: true,
        name: "Agent Alpha",
        description: "desc",
        instructions: "be concise",
        runtime_prompts: { retrieval_context: "Use retrieved context." },
        default_model_ref: "safe-small",
        tool_refs: [],
        runtime_constraints: { internet_required: false, sandbox_required: false },
      },
      "token",
    );
    await validateCatalogAgent("agent.alpha", "token");
    await previewCatalogAgentPrompt(
      {
        publish: false,
        name: "Agent Alpha",
        description: "desc",
        instructions: "be concise",
        runtime_prompts: { retrieval_context: "Use retrieved context." },
        default_model_ref: null,
        tool_refs: [],
        runtime_constraints: { internet_required: false, sandbox_required: false },
      },
      "token",
    );
    await createCatalogTool(
      {
        id: "tool.web_search",
        publish: true,
        name: "Web search",
        description: "desc",
        transport: "mcp",
        connection_profile_ref: "default",
        tool_name: "web_search",
        input_schema: {},
        output_schema: {},
        safety_policy: {},
        offline_compatible: false,
      },
      "token",
    );
    await updateCatalogTool(
      "tool.web_search",
      {
        publish: false,
        name: "Web search",
        description: "desc",
        transport: "mcp",
        connection_profile_ref: "default",
        tool_name: "web_search",
        input_schema: {},
        output_schema: {},
        safety_policy: {},
        offline_compatible: false,
      },
      "token",
    );
    await validateCatalogTool("tool.web_search", "token");
    await testCatalogTool("tool.web_search", { query: "OpenAI" }, "token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/catalog/agents/agent.alpha/validate",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/catalog/agents/prompt-preview",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/catalog/tools/tool.web_search/validate",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/catalog/tools/tool.web_search/test",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ input: { query: "OpenAI" } }),
      }),
    );
  });
});
