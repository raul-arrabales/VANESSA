import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlaygroundSessionDetail, PlaygroundSessionSummary } from "../../api/playgrounds";
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

function summary(overrides: Partial<PlaygroundSessionSummary> = {}): PlaygroundSessionSummary {
  return {
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
    ...overrides,
  };
}

function detail(overrides: Partial<PlaygroundSessionDetail> = {}): PlaygroundSessionDetail {
  return {
    ...summary(overrides),
    messages: [],
    ...overrides,
  };
}

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
    playgroundApiMocks.createPlaygroundSession.mockResolvedValue(detail());
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue(detail());
  });

  it("mounts Vanessa through the shared playground workspace with a fixed assistant identity", async () => {
    await renderWithAppProviders(<VanessaCorePage />);

    expect(await screen.findByText("Chat with Vanessa in the Vanessa AI workspace.")).toBeVisible();
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

    expect(await screen.findByText("Chat with Vanessa in the Vanessa AI workspace.")).toBeVisible();
    const shell = document.querySelector(".chatbot-shell");
    if (!(shell instanceof HTMLElement)) {
      throw new Error("Expected chatbot shell to be present");
    }

    expect(shell).toHaveAttribute("data-history-collapsed", "false");

    await userEvent.click(screen.getByRole("button", { name: "Collapse conversation history" }));

    expect(shell).toHaveAttribute("data-history-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand conversation history" })).toBeVisible();
    expect(screen.getByRole("button", { name: "New chat" })).toBeVisible();
    expect(screen.queryByText("Chat with Vanessa in the Vanessa AI workspace.")).toBeNull();
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("uses the shared modal dialogs for saved Vanessa session actions", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      summary({
        id: "sess-vanessa",
        title: "Vanessa Core",
      }),
    ]);
    playgroundApiMocks.getPlaygroundSession.mockResolvedValueOnce(detail());
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValueOnce(
      summary({
        title: "Vanessa Planning Session",
      }),
    );

    await renderWithAppProviders(<VanessaCorePage />);

    await screen.findByRole("button", { name: /^Vanessa Core/i });
    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Vanessa Core" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Rename" }));

    expect(await screen.findByRole("dialog", { name: "Rename conversation" })).toBeVisible();
    await userEvent.clear(screen.getByLabelText("Conversation title"));
    await userEvent.type(screen.getByLabelText("Conversation title"), "Vanessa Planning Session");
    await userEvent.click(screen.getByRole("button", { name: "Save title" }));

    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "sess-vanessa",
      { title: "Vanessa Planning Session" },
      "token",
    ));
    expect(await screen.findByRole("button", { name: /^Vanessa Planning Session/i })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Vanessa Planning Session" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(await screen.findByRole("dialog", { name: "Delete conversation" })).toBeVisible();
  });
});
