import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  activateDeploymentProfile,
  listPlatformCapabilities,
  listPlatformDeployments,
  listPlatformProviders,
  validatePlatformProvider,
} from "./platform";

describe("platform api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches platform capabilities with auth headers", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        capabilities: [],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listPlatformCapabilities("token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/platform/capabilities",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
  });

  it("fetches providers and deployments through the shared helper", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.endsWith("/providers")) {
          return JSON.stringify({ providers: [] });
        }
        return JSON.stringify({ deployments: [] });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listPlatformProviders("token");
    await listPlatformDeployments("token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/platform/providers",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/platform/deployments",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
  });

  it("posts validate and activate requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.includes("/validate")) {
          return JSON.stringify({
            provider: { id: "provider-1", slug: "vllm-local-gateway" },
            validation: { health: { reachable: true, status_code: 200 } },
          });
        }
        return JSON.stringify({
          deployment_profile: {
            id: "deployment-1",
            slug: "local-default",
            display_name: "Local Default",
            description: "",
            is_active: true,
            bindings: [],
          },
        });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await validatePlatformProvider("provider-1", "token");
    await activateDeploymentProfile("deployment-1", "token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/platform/providers/provider-1/validate",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/platform/deployments/deployment-1/activate",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
  });
});
