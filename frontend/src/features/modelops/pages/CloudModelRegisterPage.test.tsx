import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CloudModelRegisterPage from "./CloudModelRegisterPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelCredentials: vi.fn(),
  listModelOpsModels: vi.fn(),
  createModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
}));

let mockRole: "user" | "admin" | "superadmin" = "user";

vi.mock("../../../api/modelops/credentials", () => ({
  listModelCredentials: modelApiMocks.listModelCredentials,
  createModelCredential: modelApiMocks.createModelCredential,
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
        api_key_last4: "1234",
        is_active: true,
      },
    ]);
    modelApiMocks.listModelOpsModels.mockResolvedValue([]);
    modelApiMocks.createModelCredential.mockResolvedValue({});
    modelApiMocks.registerManagedModel.mockResolvedValue({ id: "gpt-private" });
  });

  it("hides platform scope controls for regular users", async () => {
    mockRole = "user";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    expect(await screen.findByRole("heading", { name: "Register cloud model" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Register cloud model" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Model access" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Register local model" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Credential scope")).toBeNull();
    expect(screen.queryByLabelText("Owner type")).toBeNull();
  });

  it("shows platform scope controls for superadmins", async () => {
    mockRole = "superadmin";
    await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    expect(await screen.findByLabelText("Credential scope")).toBeVisible();
    expect(screen.getByRole("link", { name: "Model access" })).toHaveAttribute("href", "/control/models/access");
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("href", "/control/models/local/register");
    expect(screen.getByLabelText("Owner type")).toBeVisible();
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
    await user.click(screen.getByRole("button", { name: "Register cloud model" }));

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
    const view = await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    await screen.findByRole("heading", { name: "Register cloud model" });
    await user.click(screen.getByRole("button", { name: "Save credential" }));

    expect(await screen.findByRole("dialog", { name: "Credentials" })).toBeVisible();
    expect(screen.getAllByText("Credential saved.")).toHaveLength(1);
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows credential save failures in the shared feedback modal instead of inline errors", async () => {
    mockRole = "superadmin";
    modelApiMocks.createModelCredential.mockRejectedValueOnce(new Error("Credential store is unavailable."));
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<CloudModelRegisterPage />, { route: "/control/models/cloud/register" });

    await screen.findByRole("heading", { name: "Register cloud model" });
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
    await user.click(screen.getByRole("button", { name: "Register cloud model" }));

    expect(await screen.findByRole("dialog", { name: "Register cloud model" })).toBeVisible();
    expect(screen.getByText("Provider model validation failed.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });
});
