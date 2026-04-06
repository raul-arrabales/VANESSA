import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../../auth/types";
import VanessaCorePage from "./pages/VanessaCorePage";
import { renderWithAppProviders } from "../../test/renderWithAppProviders";

const playgroundApiMocks = vi.hoisted(() => ({
  getPlaygroundModelOptions: vi.fn(),
  getPlaygroundKnowledgeBaseOptions: vi.fn(),
  listPlaygroundSessions: vi.fn(),
  createPlaygroundSession: vi.fn(),
  getPlaygroundSession: vi.fn(),
  updatePlaygroundSession: vi.fn(),
  deletePlaygroundSession: vi.fn(),
  streamPlaygroundMessage: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../../api/playgrounds", () => ({
  getPlaygroundModelOptions: playgroundApiMocks.getPlaygroundModelOptions,
  getPlaygroundKnowledgeBaseOptions: playgroundApiMocks.getPlaygroundKnowledgeBaseOptions,
  listPlaygroundSessions: playgroundApiMocks.listPlaygroundSessions,
  createPlaygroundSession: playgroundApiMocks.createPlaygroundSession,
  getPlaygroundSession: playgroundApiMocks.getPlaygroundSession,
  updatePlaygroundSession: playgroundApiMocks.updatePlaygroundSession,
  deletePlaygroundSession: playgroundApiMocks.deletePlaygroundSession,
  sendPlaygroundMessage: vi.fn(),
  streamPlaygroundMessage: playgroundApiMocks.streamPlaygroundMessage,
}));

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: "token",
    isAuthenticated: Boolean(mockUser),
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
  }),
}));

describe("VanessaCorePage", () => {
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
    playgroundApiMocks.getPlaygroundModelOptions.mockResolvedValue({
      assistants: [
        {
          assistant_ref: "assistant.playground.chat",
          display_name: "Chat Assistant",
          description: "General chat",
          playground_kind: "chat",
          agent_id: null,
          knowledge_required: false,
        },
        {
          assistant_ref: "assistant.vanessa.core",
          display_name: "Vanessa Core",
          description: "First-party assistant",
          playground_kind: "chat",
          agent_id: null,
          knowledge_required: false,
        },
      ],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
    });
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValue({
      knowledge_bases: [],
      default_knowledge_base_id: null,
      selection_required: false,
      configuration_message: null,
    });
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValue([]);
    playgroundApiMocks.createPlaygroundSession.mockResolvedValue({
      id: "sess-vanessa",
      playground_kind: "chat",
      assistant_ref: "assistant.vanessa.core",
      title: "Vanessa Core",
      title_source: "auto",
      model_selection: { model_id: "safe-small" },
      knowledge_binding: { knowledge_base_id: null },
      message_count: 0,
      created_at: "2026-03-18T11:00:00Z",
      updated_at: "2026-03-18T11:00:00Z",
      messages: [],
    });
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue({
      id: "sess-vanessa",
      playground_kind: "chat",
      assistant_ref: "assistant.vanessa.core",
      title: "Vanessa Core",
      title_source: "auto",
      model_selection: { model_id: "safe-small" },
      knowledge_binding: { knowledge_base_id: null },
      message_count: 0,
      created_at: "2026-03-18T11:00:00Z",
      updated_at: "2026-03-18T11:00:00Z",
      messages: [],
    });
  });

  it("mounts Vanessa through the shared playground workspace with a fixed assistant identity", async () => {
    await renderWithAppProviders(<VanessaCorePage />);

    expect(await screen.findByText("Work with Vanessa as a first-party assistant inside the Vanessa AI workspace.")).toBeVisible();
    expect(screen.getByLabelText("Model")).toBeVisible();
    expect(screen.queryByLabelText("Assistant")).toBeNull();
    expect(screen.queryByLabelText("Knowledge base")).toBeNull();

    await waitFor(() => {
      expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
        {
          playground_kind: "chat",
          assistant_ref: "assistant.vanessa.core",
          model_selection: { model_id: "safe-small" },
          knowledge_binding: { knowledge_base_id: null },
        },
        "token",
      );
    });
  });

  it("collapses Vanessa history into a slim rail and keeps the shared controls accessible", async () => {
    await renderWithAppProviders(<VanessaCorePage />);

    expect(await screen.findByText("Work with Vanessa as a first-party assistant inside the Vanessa AI workspace.")).toBeVisible();
    const shell = document.querySelector(".chatbot-shell");
    if (!(shell instanceof HTMLElement)) {
      throw new Error("Expected chatbot shell to be present");
    }

    expect(shell).toHaveAttribute("data-history-collapsed", "false");

    await userEvent.click(screen.getByRole("button", { name: "Collapse conversation history" }));

    expect(shell).toHaveAttribute("data-history-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand conversation history" })).toBeVisible();
    expect(screen.getByRole("button", { name: "New Vanessa session" })).toBeVisible();
    expect(screen.queryByText("Work with Vanessa as a first-party assistant inside the Vanessa AI workspace.")).toBeNull();
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });
});
