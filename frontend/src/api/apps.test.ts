import { beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_TOKEN_STORAGE_KEY } from "../auth/storage";
import { getApp, listApps } from "./apps";

describe("apps api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("falls back to the stored auth token when listApps receives an empty token", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stored-token");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ apps: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listApps("");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/apps",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer stored-token" }),
        credentials: "same-origin",
      }),
    );
  });

  it("falls back to the stored auth token when getApp receives an empty token", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stored-token");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        app: {
          id: "app-1",
          agent_id: "agent.workflow",
          name: "Support",
          description: "Support app",
          interface_type: "chat",
          channel_type: "vanessa_webapp",
          agent_type: "workflow",
          published_at: null,
          updated_at: null,
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await getApp("app-1", "");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/apps/app-1",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer stored-token" }),
        credentials: "same-origin",
      }),
    );
  });
});
