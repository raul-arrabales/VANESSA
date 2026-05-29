import { beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_TOKEN_STORAGE_KEY } from "../auth/storage";
import { listAgentProjects } from "./agentProjects";

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
      }),
    );
  });
});
