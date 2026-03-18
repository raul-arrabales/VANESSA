import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatConversationDetail, ChatConversationSummary, SendChatMessageResult } from "../api/chat";
import type { AuthUser } from "../auth/types";
import ChatbotPage from "./ChatbotPage";
import TestRouter from "../test/TestRouter";

const modelApiMocks = vi.hoisted(() => ({
  listEnabledModels: vi.fn(),
}));

const chatApiMocks = vi.hoisted(() => ({
  listChatConversations: vi.fn(),
  createChatConversation: vi.fn(),
  getChatConversation: vi.fn(),
  updateChatConversation: vi.fn(),
  deleteChatConversation: vi.fn(),
  sendChatMessage: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/models", () => ({
  listEnabledModels: modelApiMocks.listEnabledModels,
}));

vi.mock("../api/chat", () => ({
  listChatConversations: chatApiMocks.listChatConversations,
  createChatConversation: chatApiMocks.createChatConversation,
  getChatConversation: chatApiMocks.getChatConversation,
  updateChatConversation: chatApiMocks.updateChatConversation,
  deleteChatConversation: chatApiMocks.deleteChatConversation,
  sendChatMessage: chatApiMocks.sendChatMessage,
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

function conversationSummary(
  id: string,
  title: string,
  overrides: Partial<ChatConversationSummary> = {},
): ChatConversationSummary {
  return {
    id,
    title,
    titleSource: "auto",
    modelId: "safe-small",
    messageCount: 0,
    createdAt: "2026-03-18T11:00:00Z",
    updatedAt: "2026-03-18T11:00:00Z",
    ...overrides,
  };
}

function conversationDetail(
  id: string,
  title: string,
  overrides: Partial<ChatConversationDetail> = {},
): ChatConversationDetail {
  return {
    ...conversationSummary(id, title, overrides),
    messages: [],
    ...overrides,
  };
}

function sendResult(
  summary: ChatConversationSummary,
  userContent: string,
  assistantContent: string,
): SendChatMessageResult {
  return {
    conversation: summary,
    messages: [
      { id: "msg-user", role: "user", content: userContent, metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
      { id: "msg-assistant", role: "assistant", content: assistantContent, metadata: {}, createdAt: "2026-03-18T11:00:01Z" },
    ],
    output: assistantContent,
  };
}

function renderChatbot(): void {
  render(
    <TestRouter>
      <ChatbotPage />
    </TestRouter>,
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
    modelApiMocks.listEnabledModels.mockResolvedValue([
      { id: "safe-small", name: "Safe Small" },
      { id: "safe-large", name: "Safe Large" },
    ]);
    chatApiMocks.listChatConversations.mockResolvedValue([
      conversationSummary("conv-1", "Thread one"),
    ]);
    chatApiMocks.getChatConversation.mockResolvedValue(conversationDetail("conv-1", "Thread one"));
    vi.spyOn(window, "prompt").mockImplementation(() => null);
    vi.spyOn(window, "confirm").mockImplementation(() => true);
  });

  it("shows backend-allowed models only", async () => {
    renderChatbot();

    const picker = await screen.findByLabelText("Model");
    expect(picker).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Small" })).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Large" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "Admin Internal" })).toBeNull();
  });

  it("creates an empty conversation when the server has none", async () => {
    chatApiMocks.listChatConversations.mockResolvedValueOnce([]);
    chatApiMocks.createChatConversation.mockResolvedValueOnce(
      conversationDetail("conv-new", "New conversation"),
    );

    renderChatbot();

    await screen.findByRole("button", { name: /New conversation/ });

    expect(chatApiMocks.createChatConversation).toHaveBeenCalledWith({ model_id: "safe-small" }, "token");
  });

  it("uses the conversation API for model changes and message sends", async () => {
    chatApiMocks.updateChatConversation.mockResolvedValueOnce(
      conversationSummary("conv-1", "Thread one", { modelId: "safe-large" }),
    );
    chatApiMocks.sendChatMessage.mockResolvedValueOnce(
      sendResult(
        conversationSummary("conv-1", "Test prompt", {
          modelId: "safe-large",
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:02Z",
        }),
        "Test prompt",
        "## hello\n\nUse `code`",
      ),
    );

    renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    await screen.findByRole("option", { name: "Safe Large" });
    await userEvent.selectOptions(screen.getByLabelText("Model"), "safe-large");
    await userEvent.type(screen.getByLabelText("Message"), "Test prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(chatApiMocks.updateChatConversation).toHaveBeenCalledWith(
      "conv-1",
      { model_id: "safe-large" },
      "token",
    ));
    expect(chatApiMocks.sendChatMessage).toHaveBeenCalledWith(
      "conv-1",
      { prompt: "Test prompt" },
      "token",
    );
    expect(await screen.findByRole("heading", { name: "hello" })).toBeVisible();
    expect(screen.getByText("code", { selector: "code" })).toBeVisible();
  });

  it("keeps user messages as plain text while rendering assistant markdown", async () => {
    chatApiMocks.sendChatMessage.mockResolvedValueOnce(
      sendResult(
        conversationSummary("conv-1", "Literal user", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:01Z",
        }),
        "**literal user**",
        "Answer with **bold**",
      ),
    );

    renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "**literal user**");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("**literal user**")).toBeVisible();
    expect(screen.getByText("bold", { selector: "strong" })).toBeVisible();
  });

  it("renders multiple conversations from the API and manages rename/delete", async () => {
    chatApiMocks.listChatConversations.mockResolvedValueOnce([
      conversationSummary("conv-1", "Thread one", { updatedAt: "2026-03-18T11:00:02Z" }),
      conversationSummary("conv-2", "Thread two", { updatedAt: "2026-03-18T11:00:01Z", messageCount: 2 }),
    ]);
    chatApiMocks.getChatConversation
      .mockResolvedValueOnce(conversationDetail("conv-1", "Thread one"))
      .mockResolvedValueOnce(conversationDetail("conv-2", "Thread two", { messageCount: 2 }));
    chatApiMocks.updateChatConversation.mockResolvedValueOnce(
      conversationSummary("conv-1", "Renamed thread", { updatedAt: "2026-03-18T11:00:03Z" }),
    );
    vi.mocked(window.prompt).mockImplementationOnce(() => "Renamed thread");

    renderChatbot();

    await screen.findByRole("button", { name: /Thread one/ });
    expect(screen.getByRole("button", { name: /Thread two/ })).toBeVisible();

    const promptSpy = vi.mocked(window.prompt);
    promptSpy.mockImplementationOnce(() => "Renamed thread");
    await userEvent.click(screen.getByRole("button", { name: "Rename" }));
    await waitFor(() => expect(chatApiMocks.updateChatConversation).toHaveBeenCalledWith(
      "conv-1",
      { title: "Renamed thread" },
      "token",
    ));
    expect(await screen.findByRole("heading", { name: "Renamed thread" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(chatApiMocks.deleteChatConversation).toHaveBeenCalledWith("conv-1", "token");
    await waitFor(() => expect(screen.queryByRole("button", { name: /Renamed thread/ })).toBeNull());
    expect(chatApiMocks.getChatConversation).toHaveBeenLastCalledWith("conv-2", "token");
  });

  it("disables new chat while an empty conversation exists and re-enables after sending", async () => {
    chatApiMocks.sendChatMessage.mockResolvedValueOnce(
      sendResult(
        conversationSummary("conv-1", "First message", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:01Z",
        }),
        "First message",
        "response",
      ),
    );
    chatApiMocks.createChatConversation.mockResolvedValueOnce(
      conversationDetail("conv-2", "New conversation"),
    );

    renderChatbot();

    const newChatButton = await screen.findByRole("button", { name: "New chat" });
    await waitFor(() => expect(newChatButton).toBeDisabled());

    await userEvent.type(screen.getByLabelText("Message"), "First message");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(newChatButton).toBeEnabled());

    await userEvent.click(newChatButton);
    expect(chatApiMocks.createChatConversation).toHaveBeenCalledWith({ model_id: "safe-small" }, "token");
    await waitFor(() => expect(newChatButton).toBeDisabled());
  });
});
