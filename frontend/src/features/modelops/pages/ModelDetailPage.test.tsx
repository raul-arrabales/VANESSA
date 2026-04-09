import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelDetailPage from "./ModelDetailPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  getManagedModel: vi.fn(),
  getManagedModelUsage: vi.fn(),
  getManagedModelValidations: vi.fn(),
  registerExistingManagedModel: vi.fn(),
  activateManagedModel: vi.fn(),
  deactivateManagedModel: vi.fn(),
  unregisterManagedModel: vi.fn(),
  deleteManagedModel: vi.fn(),
}));

let mockUser: {
  id: number;
  username: string;
  email: string;
  role: "user" | "admin" | "superadmin";
  is_active: boolean;
} = { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true };

vi.mock("../../../api/modelops/models", () => ({
  getManagedModel: modelApiMocks.getManagedModel,
  getManagedModelUsage: modelApiMocks.getManagedModelUsage,
  getManagedModelValidations: modelApiMocks.getManagedModelValidations,
  registerExistingManagedModel: modelApiMocks.registerExistingManagedModel,
  activateManagedModel: modelApiMocks.activateManagedModel,
  deactivateManagedModel: modelApiMocks.deactivateManagedModel,
  unregisterManagedModel: modelApiMocks.unregisterManagedModel,
  deleteManagedModel: modelApiMocks.deleteManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: "token",
  }),
}));

describe("ModelDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 1,
      visibility_scope: "private",
      lifecycle_state: "registered",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
    });
    modelApiMocks.getManagedModelUsage.mockResolvedValue({
      model_id: "gpt-private",
      usage: { total_requests: 2, metrics: {} },
    });
    modelApiMocks.getManagedModelValidations.mockResolvedValue({
      model_id: "gpt-private",
      validations: [],
    });
  });

  it("shows user lifecycle actions only for owned models", async () => {
    mockUser = { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true };
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    expect(await screen.findByRole("heading", { name: "GPT Private" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Activate" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Activate" })).toBeDisabled();
    expect(screen.getByText("Activation requires current successful validation.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Test model" })).toBeNull();
  });

  it("enables activate when validation is current and successful", async () => {
    mockUser = { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true };
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 1,
      visibility_scope: "private",
      lifecycle_state: "validated",
      is_validation_current: true,
      last_validation_status: "success",
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    expect(await screen.findByRole("button", { name: "Activate" })).toBeEnabled();
    expect(screen.queryByText("Activation requires current successful validation.")).toBeNull();
  });

  it("shows deactivate instead of activate for active models", async () => {
    mockUser = { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true };
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 1,
      visibility_scope: "private",
      lifecycle_state: "active",
      is_validation_current: true,
      last_validation_status: "success",
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    expect(await screen.findByRole("button", { name: "Deactivate" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Activate" })).toBeNull();
  });

  it("shows access-management link and test action for admin users", async () => {
    mockUser = { id: 2, username: "admin", email: "admin@example.com", role: "admin", is_active: true };
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    expect(await screen.findByRole("link", { name: "Test model" })).toHaveAttribute(
      "href",
      "/control/models/gpt-private/test",
    );
    expect(await screen.findByRole("link", { name: "Manage access" })).toHaveAttribute(
      "href",
      "/control/models/access?modelId=gpt-private",
    );
  });

  it("opens shared modal feedback for lifecycle mutation failures without inline errors", async () => {
    const user = userEvent.setup();
    mockUser = { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true };
    modelApiMocks.getManagedModel.mockResolvedValue({
      id: "gpt-private",
      name: "GPT Private",
      provider: "openai_compatible",
      provider_model_id: "gpt-4.1",
      backend: "external_api",
      hosting: "cloud",
      owner_type: "user",
      owner_user_id: 1,
      visibility_scope: "private",
      lifecycle_state: "validated",
      is_validation_current: true,
      last_validation_status: "success",
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
    });
    modelApiMocks.activateManagedModel.mockRejectedValue(new Error("Activation request failed."));

    const view = await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    await user.click(await screen.findByRole("button", { name: "Activate" }));

    const dialog = await screen.findByRole("dialog", { name: "Model detail" });
    expect(within(dialog).getByText("Activation request failed.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });
});
