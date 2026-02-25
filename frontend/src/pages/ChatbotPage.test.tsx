import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../auth/types";
import ChatbotPage from "./ChatbotPage";

const modelApiMocks = vi.hoisted(() => ({
  listEnabledModels: vi.fn(),
  runInference: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/models", () => ({
  listEnabledModels: modelApiMocks.listEnabledModels,
  runInference: modelApiMocks.runInference,
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: "token",
    isAuthenticated: Boolean(mockUser),
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
    activatePendingUser: vi.fn(),
    listPendingUsers: vi.fn(),
    updateUserRole: vi.fn(),
  }),
}));

function renderChatbot(): void {
  render(
    <MemoryRouter>
      <ChatbotPage />
    </MemoryRouter>,
  );
}

describe("ChatbotPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    mockUser = {
      id: 10,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };
  });

  it("shows backend-allowed models only", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValueOnce([
      { id: "safe-small", name: "Safe Small" },
      { id: "safe-large", name: "Safe Large" },
    ]);

    renderChatbot();

    const picker = await screen.findByLabelText("Model");
    expect(picker).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Small" })).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Large" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "Admin Internal" })).toBeNull();
  });

  it("includes selected model and conversation context in inference requests", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValueOnce([
      { id: "safe-small", name: "Safe Small" },
      { id: "safe-large", name: "Safe Large" },
    ]);
    modelApiMocks.runInference.mockResolvedValue({ output: "hello" });

    renderChatbot();

    await screen.findByRole("option", { name: "Safe Large" });
    await userEvent.selectOptions(screen.getByLabelText("Model"), "safe-large");
    await userEvent.type(screen.getByLabelText("Message"), "Test prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(modelApiMocks.runInference).toHaveBeenCalledWith(
      "Test prompt",
      "safe-large",
      "token",
      [{ role: "user", content: "Test prompt" }],
    );
  });

  it("supports multiple conversations", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValueOnce([
      { id: "safe-small", name: "Safe Small" },
    ]);
    modelApiMocks.runInference.mockResolvedValue({ output: "response" });

    renderChatbot();

    await screen.findByLabelText("Model");
    await userEvent.type(screen.getByLabelText("Message"), "First thread message");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await userEvent.click(screen.getByRole("button", { name: "New chat" }));
    await userEvent.type(screen.getByLabelText("Message"), "Second thread");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByRole("button", { name: /First thread message/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /Second thread/ })).toBeVisible();
  });
});
