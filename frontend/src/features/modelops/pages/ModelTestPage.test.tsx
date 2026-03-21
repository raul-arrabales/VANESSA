import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelTestPage from "./ModelTestPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  getManagedModel: vi.fn(),
  listManagedModelTests: vi.fn(),
  runManagedModelTest: vi.fn(),
  validateManagedModel: vi.fn(),
}));

vi.mock("../../../api/models", () => ({
  getManagedModel: modelApiMocks.getManagedModel,
  listManagedModelTests: modelApiMocks.listManagedModelTests,
  runManagedModelTest: modelApiMocks.runManagedModelTest,
  validateManagedModel: modelApiMocks.validateManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 2, username: "admin", email: "admin@example.com", role: "admin", is_active: true },
    token: "token",
  }),
}));

describe("ModelTestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    expect(await screen.findByText("hello back")).toBeVisible();
    expect(await screen.findByRole("button", { name: "Mark as validated" })).toBeEnabled();
  });
});
