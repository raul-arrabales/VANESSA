import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  streamChatMessage: vi.fn(),
}));
const feedbackMocks = vi.hoisted(() => ({
  showErrorFeedback: vi.fn(),
  showSuccessFeedback: vi.fn(),
}));
const scrollIntoViewMock = vi.fn();
const scrollToMock = vi.fn();

let mockUser: AuthUser | null = null;

vi.mock("../api/modelops", () => ({
  listEnabledModels: modelApiMocks.listEnabledModels,
}));

vi.mock("../components/ChatMessageBody", () => ({
  default: ({ content, renderMarkdown }: { content: string; renderMarkdown: boolean }) => (
    renderMarkdown ? <pre data-testid="markdown-message">{content}</pre> : <p className="chatbot-message-text">{content}</p>
  ),
}));

vi.mock("../api/chat", () => ({
  listChatConversations: chatApiMocks.listChatConversations,
  createChatConversation: chatApiMocks.createChatConversation,
  getChatConversation: chatApiMocks.getChatConversation,
  updateChatConversation: chatApiMocks.updateChatConversation,
  deleteChatConversation: chatApiMocks.deleteChatConversation,
  streamChatMessage: chatApiMocks.streamChatMessage,
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

vi.mock("../feedback/ActionFeedbackProvider", () => ({
  useActionFeedback: () => ({
    showErrorFeedback: feedbackMocks.showErrorFeedback,
    showSuccessFeedback: feedbackMocks.showSuccessFeedback,
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

function renderChatbot() {
  return render(
    <TestRouter>
      <ChatbotPage />
    </TestRouter>,
  );
}

function getChatThread(container: HTMLElement): HTMLDivElement {
  const thread = container.querySelector(".chatbot-thread");
  if (!(thread instanceof HTMLDivElement)) {
    throw new Error("Expected chatbot thread to be present");
  }
  return thread;
}

function setThreadMetrics(
  thread: HTMLDivElement,
  {
    scrollTop,
    scrollHeight = 1000,
    clientHeight = 400,
  }: {
    scrollTop: number;
    scrollHeight?: number;
    clientHeight?: number;
  },
): void {
  Object.defineProperties(thread, {
    scrollTop: {
      configurable: true,
      writable: true,
      value: scrollTop,
    },
    scrollHeight: {
      configurable: true,
      value: scrollHeight,
    },
    clientHeight: {
      configurable: true,
      value: clientHeight,
    },
  });
}

describe("ChatbotPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    feedbackMocks.showErrorFeedback.mockReset();
    feedbackMocks.showSuccessFeedback.mockReset();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoViewMock,
    });
    Object.defineProperty(HTMLDivElement.prototype, "scrollTo", {
      configurable: true,
      value: scrollToMock,
    });
    scrollIntoViewMock.mockReset();
    scrollToMock.mockReset();
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

  it("uses the conversation API for model changes and streamed message sends", async () => {
    chatApiMocks.updateChatConversation.mockResolvedValueOnce(
      conversationSummary("conv-1", "Thread one", { modelId: "safe-large" }),
    );
    chatApiMocks.streamChatMessage.mockResolvedValueOnce(
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
    expect(chatApiMocks.streamChatMessage).toHaveBeenCalledWith(
      "conv-1",
      { prompt: "Test prompt" },
      "token",
      expect.any(Object),
    );
    await waitFor(() => {
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("## hello");
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("Use `code`");
    });
  });

  it("keeps user messages as plain text while rendering assistant markdown", async () => {
    chatApiMocks.streamChatMessage.mockResolvedValueOnce(
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
    expect(await screen.findByTestId("markdown-message")).toHaveTextContent("Answer with **bold**");
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
    chatApiMocks.streamChatMessage.mockResolvedValueOnce(
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

  it("renders assistant text incrementally while the stream is active", async () => {
    let resolveStream: (value: SendChatMessageResult) => void = () => {};
    chatApiMocks.streamChatMessage.mockImplementationOnce(
      async (_conversationId, _payload, _token, options) => {
        options?.onDelta?.("## hello");
        options?.onDelta?.("\n\n`code`");
        return await new Promise<SendChatMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "Stream prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("## hello");
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("`code`");
    });
    expect(screen.getByRole("button", { name: "Streaming..." })).toBeDisabled();

    resolveStream(
      sendResult(
        conversationSummary("conv-1", "Stream prompt", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:02Z",
        }),
        "Stream prompt",
        "## hello\n\n`code`",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
    expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled();
  });

  it("autoscrolls on send and continues following streamed deltas while pinned", async () => {
    let resolveStream: (value: SendChatMessageResult) => void = () => {};
    chatApiMocks.streamChatMessage.mockImplementationOnce(
      async (_conversationId, _payload, _token, options) => {
        options?.onDelta?.("hello");
        options?.onDelta?.(" world");
        return await new Promise<SendChatMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    const { container } = renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 600 });
    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();

    await userEvent.type(screen.getByLabelText("Message"), "Keep pinned");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollIntoViewMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Jump to latest" })).toBeNull();
    expect(await screen.findByText("hello world")).toBeVisible();

    resolveStream(
      sendResult(
        conversationSummary("conv-1", "Keep pinned", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:02Z",
        }),
        "Keep pinned",
        "hello world",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
  });

  it("pauses autoscroll when the user scrolls up and resumes from jump to latest", async () => {
    let resolveStream: (value: SendChatMessageResult) => void = () => {};
    let streamOptions: { onDelta?: (text: string) => void } | undefined;

    chatApiMocks.streamChatMessage.mockImplementationOnce(
      async (_conversationId, _payload, _token, options) => {
        streamOptions = options;
        return await new Promise<SendChatMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    const { container } = renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 600 });

    await userEvent.type(screen.getByLabelText("Message"), "Detach from stream");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(streamOptions).toBeDefined());
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollIntoViewMock).not.toHaveBeenCalled();

    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);

    await act(async () => {
      streamOptions?.onDelta?.("new token");
    });

    expect(scrollToMock).not.toHaveBeenCalled();
    expect(scrollIntoViewMock).not.toHaveBeenCalled();
    const jumpButton = await screen.findByRole("button", { name: "Jump to latest" });
    expect(jumpButton).toBeVisible();

    await userEvent.click(jumpButton);
    expect(scrollToMock).toHaveBeenCalledTimes(1);
    expect(scrollIntoViewMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Jump to latest" })).toBeNull();

    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();
    await act(async () => {
      streamOptions?.onDelta?.(" more");
    });
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollIntoViewMock).not.toHaveBeenCalled();

    resolveStream(
      sendResult(
        conversationSummary("conv-1", "Detach from stream", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:02Z",
        }),
        "Detach from stream",
        "new token more",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
  });

  it("resets follow mode when sending a new prompt and when switching conversations", async () => {
    chatApiMocks.getChatConversation
      .mockResolvedValueOnce(conversationDetail("conv-1", "Thread one", {
        messageCount: 2,
        messages: [
          { id: "msg-1", role: "assistant", content: "Existing reply", metadata: {}, createdAt: "2026-03-18T10:59:00Z" },
        ],
      }))
      .mockResolvedValueOnce(conversationDetail("conv-2", "Thread two", {
        messageCount: 2,
        messages: [
          { id: "msg-2", role: "assistant", content: "Second thread", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
        ],
      }));
    chatApiMocks.listChatConversations.mockResolvedValueOnce([
      conversationSummary("conv-1", "Thread one", { messageCount: 2, updatedAt: "2026-03-18T11:00:02Z" }),
      conversationSummary("conv-2", "Thread two", { messageCount: 2, updatedAt: "2026-03-18T11:00:01Z" }),
    ]);
    chatApiMocks.streamChatMessage.mockResolvedValueOnce(
      sendResult(
        conversationSummary("conv-1", "Fresh send", {
          messageCount: 4,
          updatedAt: "2026-03-18T11:00:03Z",
        }),
        "Fresh send",
        "response",
      ),
    );

    const { container } = renderChatbot();

    await screen.findByText("Existing reply");
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);
    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();

    await userEvent.type(screen.getByLabelText("Message"), "Fresh send");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollIntoViewMock).not.toHaveBeenCalled();

    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);

    await userEvent.click(screen.getByRole("button", { name: /Thread two/ }));
    await screen.findByText("Second thread");
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollIntoViewMock).not.toHaveBeenCalled();
  });

  it("restores the draft and removes the transient assistant reply when streaming fails", async () => {
    chatApiMocks.streamChatMessage.mockRejectedValueOnce(new Error("Stream failed"));

    renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "Broken prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByLabelText("Message")).toHaveValue("Broken prompt"));
    expect(screen.queryByRole("heading", { name: "hello" })).toBeNull();
    expect(feedbackMocks.showErrorFeedback).toHaveBeenCalledWith(expect.any(Error), "Message request failed.");
  });

  it("disables conversation controls while a stream is active", async () => {
    let resolveStream: (value: SendChatMessageResult) => void = () => {};
    chatApiMocks.streamChatMessage.mockImplementationOnce(
      async () => await new Promise<SendChatMessageResult>((resolve) => {
        resolveStream = resolve;
      }),
    );

    renderChatbot();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "Lock controls");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByRole("button", { name: "New chat" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rename" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Model" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Thread one/ })).toBeDisabled();

    resolveStream(
      sendResult(
        conversationSummary("conv-1", "Lock controls", {
          messageCount: 2,
          updatedAt: "2026-03-18T11:00:02Z",
        }),
        "Lock controls",
        "done",
      ),
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled());
  });
});
