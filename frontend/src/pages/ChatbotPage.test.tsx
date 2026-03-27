import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  PlaygroundSessionDetail,
  PlaygroundSessionSummary,
  SendPlaygroundMessageResult,
} from "../api/playgrounds";
import type { AuthUser } from "../auth/types";
import ChatPlaygroundPage from "../features/playgrounds/pages/ChatPlaygroundPage";
import TestRouter from "../test/TestRouter";

const playgroundApiMocks = vi.hoisted(() => ({
  getPlaygroundOptions: vi.fn(),
  listPlaygroundSessions: vi.fn(),
  createPlaygroundSession: vi.fn(),
  getPlaygroundSession: vi.fn(),
  updatePlaygroundSession: vi.fn(),
  deletePlaygroundSession: vi.fn(),
  streamPlaygroundMessage: vi.fn(),
}));
const feedbackMocks = vi.hoisted(() => ({
  showErrorFeedback: vi.fn(),
  showSuccessFeedback: vi.fn(),
}));
const scrollIntoViewMock = vi.fn();
const scrollToMock = vi.fn();

let mockUser: AuthUser | null = null;

vi.mock("../components/ChatMessageBody", () => ({
  default: ({ content, renderMarkdown }: { content: string; renderMarkdown: boolean }) => (
    renderMarkdown ? <pre data-testid="markdown-message">{content}</pre> : <p className="chatbot-message-text">{content}</p>
  ),
}));

vi.mock("../api/playgrounds", () => ({
  getPlaygroundOptions: playgroundApiMocks.getPlaygroundOptions,
  listPlaygroundSessions: playgroundApiMocks.listPlaygroundSessions,
  createPlaygroundSession: playgroundApiMocks.createPlaygroundSession,
  getPlaygroundSession: playgroundApiMocks.getPlaygroundSession,
  updatePlaygroundSession: playgroundApiMocks.updatePlaygroundSession,
  deletePlaygroundSession: playgroundApiMocks.deletePlaygroundSession,
  sendPlaygroundMessage: vi.fn(),
  streamPlaygroundMessage: playgroundApiMocks.streamPlaygroundMessage,
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
  }),
}));

vi.mock("../feedback/ActionFeedbackProvider", () => ({
  useActionFeedback: () => ({
    showErrorFeedback: feedbackMocks.showErrorFeedback,
    showSuccessFeedback: feedbackMocks.showSuccessFeedback,
  }),
}));

function sessionSummary(
  id: string,
  title: string,
  overrides: Partial<PlaygroundSessionSummary> = {},
): PlaygroundSessionSummary {
  return {
    id,
    playground_kind: "chat",
    assistant_ref: "assistant.playground.chat",
    title,
    title_source: "auto",
    model_selection: { model_id: "safe-small" },
    knowledge_binding: { knowledge_base_id: null },
    message_count: 0,
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
    ...overrides,
  };
}

function sessionDetail(
  id: string,
  title: string,
  overrides: Partial<PlaygroundSessionDetail> = {},
): PlaygroundSessionDetail {
  return {
    ...sessionSummary(id, title, overrides),
    messages: [],
    ...overrides,
  };
}

function sendResult(
  summary: PlaygroundSessionSummary,
  userContent: string,
  assistantContent: string,
): SendPlaygroundMessageResult {
  return {
    session: {
      ...summary,
      messages: [
        { id: "msg-user", role: "user", content: userContent, metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
        { id: "msg-assistant", role: "assistant", content: assistantContent, metadata: {}, createdAt: "2026-03-18T11:00:01Z" },
      ],
    },
    messages: [
      { id: "msg-user", role: "user", content: userContent, metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
      { id: "msg-assistant", role: "assistant", content: assistantContent, metadata: {}, createdAt: "2026-03-18T11:00:01Z" },
    ],
    output: assistantContent,
  };
}

function renderChatPlayground() {
  return render(
    <TestRouter>
      <ChatPlaygroundPage />
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

describe("ChatPlaygroundPage", () => {
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
    window.localStorage.clear();
    playgroundApiMocks.getPlaygroundOptions.mockResolvedValue({
      assistants: [],
      models: [
        { id: "safe-small", display_name: "Safe Small" },
        { id: "safe-large", display_name: "Safe Large" },
      ],
      knowledge_bases: [],
      default_knowledge_base_id: null,
      selection_required: false,
      configuration_message: null,
    });
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValue([
      sessionSummary("conv-1", "Thread one"),
    ]);
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue(sessionDetail("conv-1", "Thread one"));
    vi.spyOn(window, "prompt").mockImplementation(() => null);
    vi.spyOn(window, "confirm").mockImplementation(() => true);
  });

  it("shows backend-allowed models only", async () => {
    renderChatPlayground();

    const picker = await screen.findByLabelText("Model");
    expect(picker).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Small" })).toBeVisible();
    expect(screen.getByRole("option", { name: "Safe Large" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "Admin Internal" })).toBeNull();
  });

  it("creates an empty session when the server has none", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([]);
    playgroundApiMocks.createPlaygroundSession.mockResolvedValueOnce(
      sessionDetail("conv-new", "New conversation"),
    );

    renderChatPlayground();

    await screen.findByRole("button", { name: /New chat/ });

    expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
      {
        playground_kind: "chat",
        assistant_ref: "assistant.playground.chat",
        model_selection: { model_id: "safe-small" },
        knowledge_binding: { knowledge_base_id: null },
      },
      "token",
    );
  });

  it("updates the model and streams a chat reply", async () => {
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValueOnce(
      sessionSummary("conv-1", "Thread one", { model_selection: { model_id: "safe-large" } }),
    );
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-1", "Test prompt", {
          model_selection: { model_id: "safe-large" },
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Test prompt",
        "## hello\n\nUse `code`",
      ),
    );

    renderChatPlayground();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.selectOptions(screen.getByLabelText("Model"), "safe-large");
    await userEvent.type(screen.getByLabelText("Message"), "Test prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "conv-1",
      { model_selection: { model_id: "safe-large" } },
      "token",
    ));
    expect(playgroundApiMocks.streamPlaygroundMessage).toHaveBeenCalledWith(
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
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-1", "Literal user", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:01Z",
        }),
        "**literal user**",
        "Answer with **bold**",
      ),
    );

    renderChatPlayground();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "**literal user**");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("**literal user**")).toBeVisible();
    expect(await screen.findByTestId("markdown-message")).toHaveTextContent("Answer with **bold**");
  });

  it("renders multiple sessions from the API and manages rename/delete", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      sessionSummary("conv-1", "Thread one", { updated_at: "2026-03-18T11:00:02Z" }),
      sessionSummary("conv-2", "Thread two", { updated_at: "2026-03-18T11:00:01Z", message_count: 2 }),
    ]);
    playgroundApiMocks.getPlaygroundSession
      .mockResolvedValueOnce(sessionDetail("conv-1", "Thread one"))
      .mockResolvedValueOnce(sessionDetail("conv-2", "Thread two", { message_count: 2 }));
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValueOnce(
      sessionSummary("conv-1", "Renamed thread", { updated_at: "2026-03-18T11:00:03Z" }),
    );
    vi.mocked(window.prompt).mockImplementationOnce(() => "Renamed thread");

    renderChatPlayground();

    await screen.findByRole("button", { name: /Thread one/ });
    expect(screen.getByRole("button", { name: /Thread two/ })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Rename" }));
    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "conv-1",
      { title: "Renamed thread" },
      "token",
    ));
    expect(await screen.findByRole("heading", { name: "Renamed thread" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(playgroundApiMocks.deletePlaygroundSession).toHaveBeenCalledWith("conv-1", "token");
    await waitFor(() => expect(screen.queryByRole("button", { name: /Renamed thread/ })).toBeNull());
    expect(playgroundApiMocks.getPlaygroundSession).toHaveBeenLastCalledWith("conv-2", "chat", "token");
  });

  it("disables new chat while an empty session exists and re-enables after sending", async () => {
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-1", "First message", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:01Z",
        }),
        "First message",
        "response",
      ),
    );
    playgroundApiMocks.createPlaygroundSession.mockResolvedValueOnce(
      sessionDetail("conv-2", "New conversation"),
    );

    renderChatPlayground();

    const newChatButton = await screen.findByRole("button", { name: "New chat" });
    await waitFor(() => expect(newChatButton).toBeDisabled());

    await userEvent.type(screen.getByLabelText("Message"), "First message");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(newChatButton).toBeEnabled());

    await userEvent.click(newChatButton);
    expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
      {
        playground_kind: "chat",
        assistant_ref: "assistant.playground.chat",
        model_selection: { model_id: "safe-small" },
        knowledge_binding: { knowledge_base_id: null },
      },
      "token",
    );
    await waitFor(() => expect(newChatButton).toBeDisabled());
  });

  it("renders assistant text incrementally while the stream is active", async () => {
    let resolveStream: (value: SendPlaygroundMessageResult) => void = () => {};
    playgroundApiMocks.streamPlaygroundMessage.mockImplementationOnce(
      async (_sessionId, _payload, _token, options) => {
        options?.onDelta?.("## hello");
        options?.onDelta?.("\n\n`code`");
        return await new Promise<SendPlaygroundMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    renderChatPlayground();

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
        sessionSummary("conv-1", "Stream prompt", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Stream prompt",
        "## hello\n\n`code`",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
    expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled();
  });

  it("autoscrolls on send and continues following streamed deltas while pinned", async () => {
    let resolveStream: (value: SendPlaygroundMessageResult) => void = () => {};
    playgroundApiMocks.streamPlaygroundMessage.mockImplementationOnce(
      async (_sessionId, _payload, _token, options) => {
        options?.onDelta?.("hello");
        options?.onDelta?.(" world");
        return await new Promise<SendPlaygroundMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    const { container } = renderChatPlayground();

    await screen.findByRole("heading", { name: "Thread one" });
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 600 });
    scrollToMock.mockClear();
    scrollIntoViewMock.mockClear();

    await userEvent.type(screen.getByLabelText("Message"), "Keep pinned");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Jump to latest" })).toBeNull();
    expect(await screen.findByText("hello world")).toBeVisible();

    resolveStream(
      sendResult(
        sessionSummary("conv-1", "Keep pinned", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Keep pinned",
        "hello world",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
  });

  it("pauses autoscroll when the user scrolls up and resumes from jump to latest", async () => {
    let resolveStream: (value: SendPlaygroundMessageResult) => void = () => {};
    let streamOptions: { onDelta?: (text: string) => void } | undefined;

    playgroundApiMocks.streamPlaygroundMessage.mockImplementationOnce(
      async (_sessionId, _payload, _token, options) => {
        streamOptions = options;
        return await new Promise<SendPlaygroundMessageResult>((resolve) => {
          resolveStream = resolve;
        });
      },
    );

    const { container } = renderChatPlayground();

    await screen.findByRole("heading", { name: "Thread one" });
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 600 });

    await userEvent.type(screen.getByLabelText("Message"), "Detach from stream");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(streamOptions).toBeDefined());
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());

    scrollToMock.mockClear();
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);

    await act(async () => {
      streamOptions?.onDelta?.("new token");
    });

    expect(scrollToMock).not.toHaveBeenCalled();
    const jumpButton = await screen.findByRole("button", { name: "Jump to latest" });
    expect(jumpButton).toBeVisible();

    await userEvent.click(jumpButton);
    expect(scrollToMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Jump to latest" })).toBeNull();

    scrollToMock.mockClear();
    await act(async () => {
      streamOptions?.onDelta?.(" more");
    });
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());

    resolveStream(
      sendResult(
        sessionSummary("conv-1", "Detach from stream", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Detach from stream",
        "new token more",
      ),
    );

    await waitFor(() => expect(screen.queryByRole("button", { name: "Streaming..." })).toBeNull());
  });

  it("resets follow mode when sending a new prompt and when switching sessions", async () => {
    playgroundApiMocks.getPlaygroundSession
      .mockResolvedValueOnce(sessionDetail("conv-1", "Thread one", {
        message_count: 2,
        messages: [
          { id: "msg-1", role: "assistant", content: "Existing reply", metadata: {}, createdAt: "2026-03-18T10:59:00Z" },
        ],
      }))
      .mockResolvedValueOnce(sessionDetail("conv-2", "Thread two", {
        message_count: 2,
        messages: [
          { id: "msg-2", role: "assistant", content: "Second thread", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
        ],
      }));
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      sessionSummary("conv-1", "Thread one", { message_count: 2, updated_at: "2026-03-18T11:00:02Z" }),
      sessionSummary("conv-2", "Thread two", { message_count: 2, updated_at: "2026-03-18T11:00:01Z" }),
    ]);
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-1", "Fresh send", {
          message_count: 4,
          updated_at: "2026-03-18T11:00:03Z",
        }),
        "Fresh send",
        "response",
      ),
    );

    const { container } = renderChatPlayground();

    await screen.findByText("Existing reply");
    const thread = getChatThread(container);
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);
    scrollToMock.mockClear();

    await userEvent.type(screen.getByLabelText("Message"), "Fresh send");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());

    scrollToMock.mockClear();
    setThreadMetrics(thread, { scrollTop: 200 });
    fireEvent.scroll(thread);

    await userEvent.click(screen.getByRole("button", { name: /Thread two/ }));
    await screen.findByText("Second thread");
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
  });

  it("restores the draft and removes the transient assistant reply when streaming fails", async () => {
    playgroundApiMocks.streamPlaygroundMessage.mockRejectedValueOnce(new Error("Stream failed"));

    renderChatPlayground();

    await screen.findByRole("heading", { name: "Thread one" });
    await userEvent.type(screen.getByLabelText("Message"), "Broken prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByLabelText("Message")).toHaveValue("Broken prompt"));
    expect(feedbackMocks.showErrorFeedback).toHaveBeenCalledWith(expect.any(Error), "Message request failed.");
  });

  it("disables conversation controls while a stream is active", async () => {
    let resolveStream: (value: SendPlaygroundMessageResult) => void = () => {};
    playgroundApiMocks.streamPlaygroundMessage.mockImplementationOnce(
      async () => await new Promise<SendPlaygroundMessageResult>((resolve) => {
        resolveStream = resolve;
      }),
    );

    renderChatPlayground();

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
        sessionSummary("conv-1", "Lock controls", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Lock controls",
        "done",
      ),
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled());
  });
});
