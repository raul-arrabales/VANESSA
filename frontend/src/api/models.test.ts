import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getManagedModel,
  listManagedModelTests,
  getManagedModelUsage,
  getManagedModelValidations,
  listLocalModelArtifacts,
  registerExistingManagedModel,
  runManagedModelTest,
  validateManagedModel,
} from "./models";

describe("models api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads managed model detail, usage, validations, tests, and local artifacts with auth", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      text: async () => {
        const url = String(input);
        if (url.endsWith("/usage")) {
          return JSON.stringify({ model_id: "gpt-4", usage: { total_requests: 3, metrics: {} } });
        }
        if (url.includes("/validations")) {
          return JSON.stringify({ model_id: "gpt-4", validations: [] });
        }
        if (url.includes("/tests")) {
          return JSON.stringify({ model_id: "gpt-4", tests: [] });
        }
        if (url.endsWith("/local-artifacts")) {
          return JSON.stringify({ artifacts: [] });
        }
        return JSON.stringify({ model: { id: "gpt-4", name: "GPT-4", backend: "external_api", provider: "openai_compatible" } });
      },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await getManagedModel("gpt-4", "token");
    await getManagedModelUsage("gpt-4", "token");
    await getManagedModelValidations("gpt-4", "token");
    await listManagedModelTests("gpt-4", "token");
    await listLocalModelArtifacts("token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/modelops/models/gpt-4",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/modelops/models/gpt-4/tests?limit=10",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/v1/modelops/local-artifacts",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  it("posts to register an existing managed model", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ model: { id: "phi-local", name: "Phi Local", backend: "local", provider: "local" } }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await registerExistingManagedModel("phi-local", "token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/modelops/models/phi-local/register",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  it("posts model tests and validation confirmation payloads", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ model: { id: "gpt-4", name: "GPT-4", backend: "external_api", provider: "openai_compatible" }, test_run: { id: "test-1" }, result: { kind: "llm", success: true } }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await runManagedModelTest("gpt-4", { inputs: { prompt: "hello" } }, "token");
    await validateManagedModel("gpt-4", "token", { testRunId: "test-1" });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/modelops/models/gpt-4/test",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ inputs: { prompt: "hello" } }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/modelops/models/gpt-4/validate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ test_run_id: "test-1" }),
      }),
    );
  });
});
