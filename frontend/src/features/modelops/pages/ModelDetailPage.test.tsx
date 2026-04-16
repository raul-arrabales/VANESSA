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
  updateManagedModelCredential: vi.fn(),
  deleteManagedModel: vi.fn(),
}));

const credentialApiMocks = vi.hoisted(() => ({
  listModelCredentials: vi.fn(),
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
  updateManagedModelCredential: modelApiMocks.updateManagedModelCredential,
  deleteManagedModel: modelApiMocks.deleteManagedModel,
}));

vi.mock("../../../api/modelops/credentials", () => ({
  listModelCredentials: credentialApiMocks.listModelCredentials,
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
      credential: {
        id: "cred-1",
        status: "active",
        provider: "openai_compatible",
        display_name: "My key",
        api_key_last4: "1234",
      },
    });
    credentialApiMocks.listModelCredentials.mockResolvedValue([]);
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
      credential: { id: "cred-1", status: "active", provider: "openai_compatible", display_name: "My key", api_key_last4: "1234" },
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
      credential: { id: "cred-1", status: "active", provider: "openai_compatible", display_name: "My key", api_key_last4: "1234" },
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

    const viewNav = await screen.findByRole("navigation", { name: "Models sections" });
    const workspaceNav = screen.getByRole("navigation", { name: "ModelOps workspace navigation" });
    expect(within(workspaceNav).getByRole("link", { name: "Models" })).toHaveAttribute("aria-current", "page");
    expect(within(workspaceNav).queryByRole("link", { name: "Model catalog" })).not.toBeInTheDocument();
    expect(within(viewNav).getByRole("link", { name: "Model catalog" })).toHaveAttribute("href", "/control/models/catalog");
    expect(within(viewNav).getByRole("link", { name: "Model details: GPT Private" })).toHaveAttribute("aria-current", "page");
    expect(within(viewNav).getByRole("link", { name: "Test model: GPT Private" })).toHaveAttribute(
      "href",
      "/control/models/gpt-private/test",
    );
    expect(screen.queryByRole("link", { name: "Test model" })).toBeNull();
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
      credential: { id: "cred-1", status: "active", provider: "openai_compatible", display_name: "My key", api_key_last4: "1234" },
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

  it("shows revoked credential status and replacement options", async () => {
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
      lifecycle_state: "inactive",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
      credential: {
        id: "cred-old",
        status: "revoked",
        provider: "openai_compatible",
        display_name: "Old key",
        api_key_last4: "1111",
      },
    });
    credentialApiMocks.listModelCredentials.mockResolvedValue([
      {
        id: "cred-new",
        owner_user_id: 1,
        credential_scope: "personal",
        provider: "openai_compatible",
        display_name: "New key",
        api_base_url: "https://api.openai.com/v1",
        api_key_last4: "2222",
        is_active: true,
        revoked_at: null,
      },
    ]);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    expect(await screen.findByRole("heading", { name: "Credential" })).toBeVisible();
    expect(screen.getByText("Credential status: Revoked")).toBeVisible();
    expect(screen.getByText("Assign a saved credential, then test and validate the model again.")).toBeVisible();
    expect(screen.getByRole("option", { name: "New key · ****2222" })).toBeVisible();
  });

  it("replaces a revoked credential and keeps activation blocked while validation is stale", async () => {
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
      lifecycle_state: "inactive",
      is_validation_current: false,
      last_validation_status: null,
      task_key: "llm",
      source: "external_provider",
      artifact: {},
      usage_summary: { total_requests: 2, metrics: {} },
      credential: {
        id: "cred-old",
        status: "revoked",
        provider: "openai_compatible",
        display_name: "Old key",
        api_key_last4: "1111",
      },
    });
    credentialApiMocks.listModelCredentials.mockResolvedValue([
      {
        id: "cred-new",
        owner_user_id: 1,
        credential_scope: "personal",
        provider: "openai_compatible",
        display_name: "New key",
        api_base_url: "https://api.openai.com/v1",
        api_key_last4: "2222",
        is_active: true,
        revoked_at: null,
      },
    ]);
    modelApiMocks.updateManagedModelCredential.mockResolvedValue({});

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/models/:modelId" element={<ModelDetailPage />} />
      </Routes>,
      { route: "/control/models/gpt-private" },
    );

    await user.selectOptions(await screen.findByLabelText("Replacement credential for OpenAI compatible"), "cred-new");
    await user.click(screen.getByRole("button", { name: "Replace credential" }));

    expect(modelApiMocks.updateManagedModelCredential).toHaveBeenCalledWith("gpt-private", "cred-new", "token");
    expect(screen.getByRole("button", { name: "Activate" })).toBeDisabled();
  });
});
