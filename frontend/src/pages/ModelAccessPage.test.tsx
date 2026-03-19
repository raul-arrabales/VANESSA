import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelAccessPage from "./ModelAccessPage";
import TestRouter from "../test/TestRouter";

const modelApiMocks = vi.hoisted(() => ({
  listModelCredentials: vi.fn(),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
  listAvailableManagedModels: vi.fn(),
}));

vi.mock("../api/models", () => ({
  listModelCredentials: modelApiMocks.listModelCredentials,
  createModelCredential: modelApiMocks.createModelCredential,
  revokeModelCredential: modelApiMocks.revokeModelCredential,
  registerManagedModel: modelApiMocks.registerManagedModel,
  listAvailableManagedModels: modelApiMocks.listAvailableManagedModels,
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "user", email: "u@example.com", role: "user", is_active: true },
    token: "token",
  }),
}));

describe("ModelAccessPage", () => {
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
    modelApiMocks.listAvailableManagedModels.mockResolvedValue([
      {
        id: "phi-3-mini",
        name: "Phi 3 Mini",
        provider: "local_filesystem",
        origin: "personal",
        backend: "local",
        source: "local_folder",
        availability: "offline_ready",
        access_scope: "private",
        credential_owner: "you",
      },
    ]);
    modelApiMocks.createModelCredential.mockResolvedValue({});
    modelApiMocks.registerManagedModel.mockResolvedValue({});
    modelApiMocks.revokeModelCredential.mockResolvedValue({});
  });

  it("renders credentials and available models", async () => {
    render(
      <TestRouter>
        <ModelAccessPage />
      </TestRouter>,
    );

    expect(await screen.findByText("My key · openai_compatible · ****1234")).toBeVisible();
    expect(screen.getByText("Phi 3 Mini")).toBeVisible();
  });

  it("creates credential and registers model", async () => {
    const user = userEvent.setup();

    render(
      <TestRouter>
        <ModelAccessPage />
      </TestRouter>,
    );

    await screen.findByText("My key · openai_compatible · ****1234");

    await user.type(screen.getByLabelText("API key"), "sk-test-key");
    await user.click(screen.getByRole("button", { name: "Save credential" }));
    expect(modelApiMocks.createModelCredential).toHaveBeenCalled();

    await user.type(screen.getByLabelText("Model id"), "gpt-private");
    await user.type(screen.getByLabelText("Model name"), "GPT Private");
    await user.selectOptions(screen.getByLabelText("Model type"), "llm");
    await user.type(screen.getByLabelText("Provider model id"), "gpt-4.1");
    await user.selectOptions(screen.getByLabelText("Credential"), "cred-1");
    await user.click(screen.getByRole("button", { name: "Register model" }));

    expect(modelApiMocks.registerManagedModel).toHaveBeenCalled();
  });
});
