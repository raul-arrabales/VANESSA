import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  createDeploymentProfile,
  createPlatformProvider,
  deleteDeploymentProfile,
  deletePlatformProvider,
  listPlatformActivationAudit,
  listPlatformCapabilities,
  listPlatformProviderFamilies,
  listPlatformDeployments,
  listPlatformProviders,
  updateDeploymentProfile,
  updatePlatformProvider,
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

  it("fetches providers, provider families, deployments, and activation audit through the shared helper", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.endsWith("/provider-families")) {
          return JSON.stringify({ provider_families: [] });
        }
        if (url.endsWith("/activation-audit")) {
          return JSON.stringify({ activation_audit: [] });
        }
        if (url.endsWith("/providers")) {
          return JSON.stringify({ providers: [] });
        }
        return JSON.stringify({ deployments: [] });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listPlatformProviders("token");
    await listPlatformProviderFamilies("token");
    await listPlatformDeployments("token");
    await listPlatformActivationAudit("token");

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
      "/api/v1/platform/provider-families",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/platform/deployments",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/platform/activation-audit",
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

  it("supports provider and deployment mutations", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.endsWith("/providers")) {
          return JSON.stringify({ provider: { id: "provider-1", slug: "provider-a" } });
        }
        if (url.includes("/providers/")) {
          return JSON.stringify({ provider: { id: "provider-1", slug: "provider-a" } });
        }
        return JSON.stringify({
          deployment_profile: {
            id: "deployment-1",
            slug: "profile-a",
            display_name: "Profile A",
            description: "",
            is_active: false,
            bindings: [],
          },
        });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await createPlatformProvider(
      {
        provider_key: "vllm_local",
        slug: "provider-a",
        display_name: "Provider A",
        description: "",
        endpoint_url: "http://llm:8000",
        healthcheck_url: null,
        enabled: true,
        config: {},
        secret_refs: {},
      },
      "token",
    );
    await updatePlatformProvider(
      "provider-1",
      {
        slug: "provider-a",
        display_name: "Provider A",
        description: "",
        endpoint_url: "http://llm:8000",
        healthcheck_url: null,
        enabled: true,
        config: {},
        secret_refs: {},
      },
      "token",
    );
    await deletePlatformProvider("provider-1", "token");
    await createDeploymentProfile(
      {
        slug: "profile-a",
        display_name: "Profile A",
        description: "",
        bindings: [],
      },
      "token",
    );
    await updateDeploymentProfile(
      "deployment-1",
      {
        slug: "profile-a",
        display_name: "Profile A",
        description: "",
        bindings: [],
      },
      "token",
    );
    await cloneDeploymentProfile(
      "deployment-1",
      {
        slug: "profile-b",
        display_name: "Profile B",
        description: "",
      },
      "token",
    );
    await deleteDeploymentProfile("deployment-1", "token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/platform/providers",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/platform/providers/provider-1",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/platform/providers/provider-1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/platform/deployments",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/v1/platform/deployments/deployment-1",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/v1/platform/deployments/deployment-1/clone",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      7,
      "/api/v1/platform/deployments/deployment-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
