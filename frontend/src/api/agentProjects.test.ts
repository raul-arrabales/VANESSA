import { beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_TOKEN_STORAGE_KEY } from "../auth/storage";
import { createAgentProject, listAgentProjects } from "./agentProjects";

describe("agentProjects api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("falls back to the stored auth token when no token argument is provided", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stored-token");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ agent_projects: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentProjects();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/agent-projects",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer stored-token" }),
        credentials: "same-origin",
      }),
    );
  });

  it("uses the stored auth token when an empty token argument is provided", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stored-token");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        agent_project: {
          id: "proj-1",
          owner_user_id: 1,
          published_agent_id: null,
          current_version: 1,
          visibility: "private",
          created_at: "2026-03-18T11:00:00Z",
          updated_at: "2026-03-18T11:00:00Z",
          spec: {
            name: "Workflow Agent",
            description: "desc",
            instructions: "",
            runtime_prompts: {},
            default_model_ref: null,
            tool_refs: [],
            mcp_server_refs: [],
            agent_domain: "default",
            agent_type: "workflow",
            channel_type: "vanessa_webapp",
            interface_type: "chat",
            workflow_definition: { version: 2, actions: [] },
            tool_policy: { allow_user_tools: false },
            runtime_constraints: { internet_required: false, sandbox_required: false },
          },
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await createAgentProject(
      {
        id: "proj-1",
        visibility: "private",
        name: "Workflow Agent",
        description: "desc",
        instructions: "",
        default_model_ref: null,
        tool_refs: [],
        mcp_server_refs: [],
        agent_domain: "default",
        agent_type: "workflow",
        channel_type: "vanessa_webapp",
        interface_type: "chat",
        workflow_definition: { version: 2, actions: [] },
        tool_policy: { allow_user_tools: false },
        runtime_constraints: { internet_required: false, sandbox_required: false },
      },
      "",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/agent-projects",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer stored-token" }),
        credentials: "same-origin",
      }),
    );
  });
});
