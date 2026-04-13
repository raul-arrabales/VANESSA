import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CloudModelRegisterPage from "./CloudModelRegisterPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelCredentials: vi.fn(),
  listModelOpsModels: vi.fn(),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
}));

let mockRole: "user" | "admin" | "superadmin" = "user";

function getCloudRegisterSubmitButton(): HTMLButtonElement {
  const button = screen
    .getAllByRole("button", { name: "Register cloud model" })
    .find((candidate) => !candidate.hasAttribute("aria-pressed"));
  expect(button).toBeInstanceOf(HTMLButtonElement);
  return button as HTMLButtonElement;
}

vi.mock("../../../api/modelops/credentials", () => ({
  listModelCredentials: modelApiMocks.listModelCredentials,
  createModelCredential: modelApiMocks.createModelCredential,
  revokeModelCredential: modelApiMocks.revokeModelCredential,
}));

vi.mock("../../../api/modelops/models", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
  registerManagedModel: modelApiMocks.registerManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "tester", email: "t@example.com", role: mockRole, is_active: true },
    token: "token",
  }),
}));

describe("CloudModelRegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelCredentials.mockResolvedValue([
      {
        id: "cred-1",
        owner_user_id: 1,
        credential_scope: "personal",
        provider: "openai_compatible",
        display_name: "My key",
        api_base_url: "https://api.openai.com/v1",
        api_key_last4: "1234",
        is_active: true,
      },
    ]);
    modelApiMocks.listModelOpsModels.mockResolvedValue([]);
    modelApiMocks.createModelCredential.mockResolvedValue({});
    modelApiMocks.revokeModelCredential.mockResolvedValue({
      id: "cred-1",
      owner_user_id: 1,
      credential_scope: "personal",
      provider: "openai_compatible",
      display_name: "My key",
      api_base_url: "https://api.openai.com/v1",
      api_key_last4: "1234",
      is_active: false,
    });
    modelApiMocks.registerManagedModel.mockResolvedValue({ id: "gpt-private" });
  });

  it("defaults to the register view and hides platform scope controls for regular users", async () => {
    mockRole = "user";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    expect(await screen.findByRole("heading", { name: "Register cloud model" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Register cloud model" })).toHaveAttribute("aria-current", "page");
    const viewNav = screen.getByRole("navigation", { name: "Cloud model registration sections" });
    expect(within(viewNav).getByRole("button", { name: "Register cloud model" })).toHaveAttribute("aria-pressed", "true");
    expect(within(viewNav).getByRole("button", { name: "Credentials" })).toBeVisible();
    expect(within(viewNav).getByRole("button", { name: "Recently registered" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Model access" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Register local model" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Credential scope")).toBeNull();
    expect(screen.queryByLabelText("Owner type")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Credentials" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recently registered cloud models" })).not.toBeInTheDocument();
  });

  it("lists saved credentials before the new credential form", async () => {
    mockRole = "superadmin";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    const savedHeading = await screen.findByRole("heading", { name: "Saved credentials" });
    const formHeading = screen.getByRole("heading", { name: "Save new credential" });
    expect(savedHeading.compareDocumentPosition(formHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const credentialList = screen.getByRole("list", { name: "Saved cloud credentials" });
    expect(credentialList).toBeVisible();
    expect(within(credentialList).getByText("My key")).toBeVisible();
    expect(within(credentialList).getByText("OpenAI compatible")).toBeVisible();
    expect(within(credentialList).getByText("Personal")).toBeVisible();
    expect(within(credentialList).getByText("https://api.openai.com/v1")).toBeVisible();
    expect(within(credentialList).getByText("****1234")).toBeVisible();
    expect(within(credentialList).getByRole("button", { name: "Revoke" })).toBeVisible();
  });

  it("closes the credential revoke confirmation without revoking when canceled", async () => {
    mockRole = "superadmin";
    const user = userEvent.setup();
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    const credentialList = await screen.findByRole("list", { name: "Saved cloud credentials" });
    await user.click(within(credentialList).getByRole("button", { name: "Revoke" }));

    expect(await screen.findByRole("dialog", { name: "Revoke credential" })).toBeVisible();
    expect(screen.getByText("Revoke My key? Models using this credential will need a new credential before they can be tested or used.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Revoke credential" })).not.toBeInTheDocument();
    expect(modelApiMocks.revokeModelCredential).not.toHaveBeenCalled();
  });

  it("revokes a saved credential after confirmation", async () => {
    mockRole = "superadmin";
    const user = userEvent.setup();
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    const credentialList = await screen.findByRole("list", { name: "Saved cloud credentials" });
    await user.click(within(credentialList).getByRole("button", { name: "Revoke" }));
    await user.click(await screen.findByRole("button", { name: "Revoke credential" }));

    expect(modelApiMocks.revokeModelCredential).toHaveBeenCalledWith("cred-1", "token");
    expect(await screen.findByRole("dialog", { name: "Credentials" })).toBeVisible();
    expect(screen.getAllByText("Credential revoked.")).toHaveLength(1);
  });

  it("shows an empty saved credential state above the new credential form", async () => {
    mockRole = "superadmin";
    modelApiMocks.listModelCredentials.mockResolvedValueOnce([]);

    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    expect(await screen.findByRole("heading", { name: "Saved credentials" })).toBeVisible();
    expect(screen.getByText("No credentials have been saved yet.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Save new credential" })).toBeVisible();
  });

  it("explains when the selected provider has no saved credentials", async () => {
    mockRole = "user";
    const user = userEvent.setup();

    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    await screen.findByRole("heading", { name: "Register cloud model" });
    await user.selectOptions(screen.getByLabelText("Provider"), "anthropic");

    const credentialSelect = screen.getByLabelText("Credential");
    const hintOption = within(credentialSelect).getByRole("option", {
      name: "No credentials saved for the selected provider.",
    });
    expect(hintOption).toBeDisabled();
    expect(credentialSelect).toHaveValue("");
  });

  it("shows platform scope controls for superadmins", async () => {
    mockRole = "superadmin";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    expect(await screen.findByLabelText("Owner type")).toBeVisible();
    expect(screen.getByRole("link", { name: "Model access" })).toHaveAttribute("href", "/control/models/access");
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("href", "/control/models/local/register");

    const viewNav = screen.getByRole("navigation", { name: "Cloud model registration sections" });
    await userEvent.click(within(viewNav).getByRole("button", { name: "Credentials" }));
    expect(await screen.findByLabelText("Credential scope")).toBeVisible();
    expect(screen.queryByLabelText("Owner type")).toBeNull();
  });

  it("switches between URL-driven subviews", async () => {
    mockRole = "user";
    const user = userEvent.setup();
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    const viewNav = await screen.findByRole("navigation", { name: "Cloud model registration sections" });
    await user.click(within(viewNav).getByRole("button", { name: "Credentials" }));
    expect(within(viewNav).getByRole("button", { name: "Credentials" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Saved credentials" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Save new credential" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Register cloud model" })).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: "Recently registered" }));
    expect(within(viewNav).getByRole("button", { name: "Recently registered" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Recently registered cloud models" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Saved credentials" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Save new credential" })).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: "Register cloud model" }));
    expect(within(viewNav).getByRole("button", { name: "Register cloud model" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Register cloud model" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Recently registered cloud models" })).not.toBeInTheDocument();
  });

  it("falls back to the register view for invalid cloud model views", async () => {
    mockRole = "user";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=unknown" });

    expect(await screen.findByRole("heading", { name: "Register cloud model" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Saved credentials" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Save new credential" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recently registered cloud models" })).not.toBeInTheDocument();
  });

  it("renders recently registered cloud models in the recent view", async () => {
    mockRole = "user";
    modelApiMocks.listModelOpsModels.mockResolvedValueOnce([
      {
        id: "gpt-private",
        name: "GPT Private",
        provider: "openai_compatible",
        backend: "external_api",
        hosting: "cloud",
        owner_type: "user",
        source: "external_provider",
        availability: "online_only",
        visibility_scope: "private",
        task_key: "llm",
        lifecycle_state: "registered",
        is_validation_current: false,
        last_validation_status: null,
      },
    ]);

    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=recent" });

    expect(await screen.findByRole("heading", { name: "Recently registered cloud models" })).toBeVisible();
    expect(screen.getByText("GPT Private")).toBeVisible();
    expect(screen.getByText("gpt-private")).toBeVisible();
  });

  it("registers a cloud model and shows the next-step detail link for regular users", async () => {
    mockRole = "user";
    const user = userEvent.setup();
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    await screen.findByRole("heading", { name: "Register cloud model" });
    await user.type(screen.getByLabelText("Model id"), "gpt-private");
    await user.type(screen.getByLabelText("Model name"), "GPT Private");
    await user.type(screen.getByLabelText("Provider model id"), "gpt-4.1");
    await user.selectOptions(screen.getByLabelText("Credential"), "cred-1");
    await user.click(getCloudRegisterSubmitButton());

    expect(modelApiMocks.registerManagedModel).toHaveBeenCalled();
    expect(await screen.findByRole("dialog", { name: "Register cloud model" })).toBeVisible();
    expect(screen.getAllByText("Model registered.")).toHaveLength(1);
    expect(await screen.findByRole("link", { name: "Open details" })).toHaveAttribute(
      "href",
      "/control/models/gpt-private",
    );
  });

  it("shows credential save success in the shared feedback modal without leaving inline feedback", async () => {
    mockRole = "superadmin";
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    await screen.findByRole("heading", { name: "Save new credential" });
    await user.click(screen.getByRole("button", { name: "Save credential" }));

    expect(await screen.findByRole("dialog", { name: "Credentials" })).toBeVisible();
    expect(screen.getAllByText("Credential saved.")).toHaveLength(1);
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows credential save failures in the shared feedback modal instead of inline errors", async () => {
    mockRole = "superadmin";
    modelApiMocks.createModelCredential.mockRejectedValueOnce(new Error("Credential store is unavailable."));
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register?view=credentials" });

    await screen.findByRole("heading", { name: "Save new credential" });
    await user.click(screen.getByRole("button", { name: "Save credential" }));

    expect(await screen.findByRole("dialog", { name: "Credentials" })).toBeVisible();
    expect(screen.getByText("Credential store is unavailable.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows cloud model registration failures in the shared feedback modal", async () => {
    mockRole = "user";
    modelApiMocks.registerManagedModel.mockRejectedValueOnce(new Error("Provider model validation failed."));
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    await screen.findByRole("heading", { name: "Register cloud model" });
    await user.type(screen.getByLabelText("Model id"), "gpt-private");
    await user.type(screen.getByLabelText("Model name"), "GPT Private");
    await user.type(screen.getByLabelText("Provider model id"), "gpt-4.1");
    await user.selectOptions(screen.getByLabelText("Credential"), "cred-1");
    await user.click(getCloudRegisterSubmitButton());

    expect(await screen.findByRole("dialog", { name: "Register cloud model" })).toBeVisible();
    expect(screen.getByText("Provider model validation failed.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });
});
