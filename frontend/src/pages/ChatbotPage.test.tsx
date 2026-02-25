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

  it("includes selected model in inference requests", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValueOnce([
      { id: "safe-small", name: "Safe Small" },
      { id: "safe-large", name: "Safe Large" },
    ]);
    modelApiMocks.runInference.mockResolvedValueOnce({ output: "hello" });

    renderChatbot();

    await screen.findByRole("option", { name: "Safe Large" });
    await userEvent.selectOptions(screen.getByLabelText("Model"), "safe-large");
    await userEvent.type(screen.getByLabelText("Prompt"), "Test prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send prompt" }));

    expect(modelApiMocks.runInference).toHaveBeenCalledWith("Test prompt", "safe-large", "token");
  });
});
