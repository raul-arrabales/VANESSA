import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelTestPage from "./ModelTestPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  getManagedModel: vi.fn(),
  listManagedModelTests: vi.fn(),
  listManagedModelTestRuntimes: vi.fn(),
  runManagedModelTest: vi.fn(),
  validateManagedModel: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  role: "admin" as "admin" | "superadmin",
}));

vi.mock("../../../api/modelops/models", () => ({
  getManagedModel: modelApiMocks.getManagedModel,
}));

vi.mock("../../../api/modelops/testing", () => ({
  listManagedModelTests: modelApiMocks.listManagedModelTests,
  listManagedModelTestRuntimes: modelApiMocks.listManagedModelTestRuntimes,
  runManagedModelTest: modelApiMocks.runManagedModelTest,
  validateManagedModel: modelApiMocks.validateManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: 2,
      username: authState.role === "superadmin" ? "root" : "admin",
      email: "admin@example.com",
      role: authState.role,
      is_active: true,
    },
    token: "token",
  }),
}));

describe("ModelTestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.role = "admin";
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1-mini",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 2,
      visibility_scope: "private",
      lifecycle_state: "registered",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 0, metrics: {} },
    });
    modelApiMocks.listManagedModelTests.mockResolvedValue({
      model_id: "gpt-private",
      tests: [],
    });
    modelApiMocks.listManagedModelTestRuntimes.mockResolvedValue({
      model_id: "gpt-private",
      runtimes: [],
      default_provider_instance_id: null,
    });
    modelApiMocks.runManagedModelTest.mockResolvedValue({
      model: {
        id: "gpt-private",
        name: "GPT Private",
        provider: "openai_compatible",
        backend: "external_api",
        hosting: "cloud",
        lifecycle_state: "registered",
        is_validation_current: false,
        last_validation_status: null,
        task_key: "llm",
        artifact: {},
      },
      test_run: {
        id: "test-1",
        model_id: "gpt-private",
        task_key: "llm",
        result: "success",
        summary: "Cloud LLM test succeeded",
        input_payload: { prompt: "hello" },
        output_payload: { choices: [] },
        error_details: {},
        latency_ms: 25,
      },
      result: {
        kind: "llm",
        success: true,
        response_text: "hello back",
        latency_ms: 25,
      },
    });
    modelApiMocks.validateManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      backend: "external_api",
      hosting: "cloud",
      lifecycle_state: "validated",
      is_validation_current: true,
      last_validation_status: "success",
      task_key: "llm",
      artifact: {},
    });
  });

  it("renders the llm test interface with default prompt", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId/test" element={<ModelTestPage />} />
      </Routes>,
      { route: "/control/models/gpt-private/test" },
    );

    expect(await screen.findByRole("heading", { name: "GPT Private" })).toBeVisible();
    expect(screen.getByLabelText("Prompt")).toHaveValue("hello");
    expect(screen.getByRole("button", { name: "Mark as validated" })).toBeDisabled();
    expect(screen.getByText("Validation stays disabled until a successful test run is recorded.")).toBeVisible();
  });

  it("keeps validation disabled when the model is already currently validated", async () => {
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1-mini",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 2,
      visibility_scope: "private",
      lifecycle_state: "active",
      is_validation_current: true,
      last_validation_status: "success",
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 0, metrics: {} },
    });
    modelApiMocks.listManagedModelTests.mockResolvedValue({
      model_id: "gpt-private",
      tests: [
        {
          id: "test-1",
          model_id: "gpt-private",
          task_key: "llm",
          result: "success",
          summary: "Cloud LLM test succeeded",
          input_payload: { prompt: "hello" },
          output_payload: { choices: [] },
          error_details: {},
          latency_ms: 25,
        },
      ],
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId/test" element={<ModelTestPage />} />
      </Routes>,
      { route: "/control/models/gpt-private/test" },
    );

    expect(await screen.findByRole("button", { name: "Mark as validated" })).toBeDisabled();
    expect(screen.getByText("This model is already validated for its current configuration.")).toBeVisible();
  });

  it("runs a test and enables validation", async () => {
    const user = userEvent.setup();
    modelApiMocks.listManagedModelTests
      .mockResolvedValueOnce({
        model_id: "gpt-private",
        tests: [],
      })
      .mockResolvedValue({
        model_id: "gpt-private",
        tests: [
          {
            id: "test-1",
            model_id: "gpt-private",
            task_key: "llm",
            result: "success",
            summary: "Cloud LLM test succeeded",
            input_payload: { prompt: "hello" },
            output_payload: { choices: [] },
            error_details: {},
            latency_ms: 25,
          },
        ],
      });
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId/test" element={<ModelTestPage />} />
      </Routes>,
      { route: "/control/models/gpt-private/test" },
    );

    await user.click(await screen.findByRole("button", { name: "Run test" }));

    expect(modelApiMocks.runManagedModelTest).toHaveBeenCalledWith(
      "gpt-private",
      { inputs: { prompt: "hello" } },
      "token",
    );
    expect((await screen.findAllByText("hello back")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: "Mark as validated" })).toBeEnabled();
  });

  it("shows runtime selection for superadmin local llm tests and sends provider override", async () => {
    authState.role = "superadmin";
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "Qwen--Qwen2.5-0.5B-Instruct",
      name: "Qwen Local",
      provider: "local",
      backend: "local",
      hosting: "local",
      owner_type: "platform",
      owner_user_id: null,
      visibility_scope: "platform",
      lifecycle_state: "registered",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "local_folder",
      artifact: { storage_path: "/models/llm/Qwen--Qwen2.5-0.5B-Instruct" },
      usage_summary: { total_requests: 0, metrics: {} },
    });
    modelApiMocks.listManagedModelTestRuntimes.mockResolvedValue({
      model_id: "Qwen--Qwen2.5-0.5B-Instruct",
      default_provider_instance_id: "provider-1",
      runtimes: [
        {
          provider_instance_id: "provider-1",
          slug: "vllm-local-gateway",
          display_name: "vLLM local gateway",
          provider_key: "vllm_local",
          endpoint_url: "http://llm:8000",
          adapter_kind: "openai_compatible_llm",
          enabled: true,
          is_active: true,
          reachable: true,
          status_code: 200,
          matches_model: true,
          matched_model_id: "local-vllm-default",
          message: "Runtime serves the selected local model",
        },
      ],
    });
    modelApiMocks.runManagedModelTest.mockResolvedValue({
      model: {
        id: "Qwen--Qwen2.5-0.5B-Instruct",
        name: "Qwen Local",
        provider: "local",
        backend: "local",
        hosting: "local",
        lifecycle_state: "registered",
        is_validation_current: false,
        last_validation_status: null,
        task_key: "llm",
        artifact: { storage_path: "/models/llm/Qwen--Qwen2.5-0.5B-Instruct" },
      },
      test_run: {
        id: "test-local-1",
        model_id: "Qwen--Qwen2.5-0.5B-Instruct",
        task_key: "llm",
        result: "success",
        summary: "Local LLM test succeeded",
        input_payload: { provider_instance_id: "provider-1", model: "local-vllm-default" },
        output_payload: { output: [] },
        error_details: {},
        latency_ms: 12,
      },
      result: {
        kind: "llm",
        success: true,
        response_text: "local hello back",
        latency_ms: 12,
      },
    });

    const user = userEvent.setup();
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId/test" element={<ModelTestPage />} />
      </Routes>,
      { route: "/control/models/Qwen--Qwen2.5-0.5B-Instruct/test" },
    );

    expect(await screen.findByLabelText("Runtime provider")).toHaveValue("provider-1");

    await user.click(screen.getByRole("button", { name: "Run test" }));

    expect(modelApiMocks.runManagedModelTest).toHaveBeenCalledWith(
      "Qwen--Qwen2.5-0.5B-Instruct",
      {
        inputs: { prompt: "hello" },
        provider_instance_id: "provider-1",
      },
      "token",
    );
  });

  it("shows compatibility guidance when no runtime serves the local model", async () => {
    authState.role = "superadmin";
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "Qwen--Qwen2.5-0.5B-Instruct",
      name: "Qwen Local",
      provider: "local",
      backend: "local",
      hosting: "local",
      owner_type: "platform",
      owner_user_id: null,
      visibility_scope: "platform",
      lifecycle_state: "registered",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "local_folder",
      artifact: { storage_path: "/models/llm/Qwen--Qwen2.5-0.5B-Instruct" },
      usage_summary: { total_requests: 0, metrics: {} },
    });
    modelApiMocks.listManagedModelTestRuntimes.mockResolvedValue({
      model_id: "Qwen--Qwen2.5-0.5B-Instruct",
      default_provider_instance_id: null,
      runtimes: [
        {
          provider_instance_id: "provider-1",
          slug: "vllm-local-gateway",
          display_name: "vLLM local gateway",
          provider_key: "vllm_local",
          endpoint_url: "http://llm:8000",
          adapter_kind: "openai_compatible_llm",
          enabled: true,
          is_active: true,
          reachable: true,
          status_code: 200,
          matches_model: false,
          matched_model_id: null,
          message: "Runtime does not currently serve the selected local model",
        },
      ],
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId/test" element={<ModelTestPage />} />
      </Routes>,
      { route: "/control/models/Qwen--Qwen2.5-0.5B-Instruct/test" },
    );

    expect(await screen.findByText("No compatible runtime currently serves this local model.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Run test" })).toBeDisabled();
  });
});
