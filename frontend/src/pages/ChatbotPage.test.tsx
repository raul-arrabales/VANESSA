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
  getPlaygroundModelOptions: vi.fn(),
  getPlaygroundKnowledgeBaseOptions: vi.fn(),
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

function getChatShell(container: HTMLElement): HTMLElement {
  const shell = container.querySelector(".chatbot-shell");
  if (!(shell instanceof HTMLElement)) {
    throw new Error("Expected chatbot shell to be present");
  }
  return shell;
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

async function openSavedChat(title = "Thread one"): Promise<void> {
  await userEvent.click(await screen.findByRole("button", { name: new RegExp(`^${title}`, "i") }));
}

async function waitForDraftReady(): Promise<void> {
  await screen.findByRole("heading", { name: "New conversation" });
  await waitFor(() => expect(screen.getByLabelText("Message")).toBeEnabled());
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
    playgroundApiMocks.getPlaygroundModelOptions.mockResolvedValue({
      assistants: [],
      models: [
        { id: "safe-small", display_name: "Safe Small" },
        { id: "safe-large", display_name: "Safe Large" },
      ],
    });
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValue({
      knowledge_bases: [],
      default_knowledge_base_id: null,
      selection_required: false,
      configuration_message: null,
    });
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValue([
      sessionSummary("conv-1", "Thread one"),
    ]);
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue(sessionDetail("conv-1", "Thread one"));
    playgroundApiMocks.createPlaygroundSession.mockResolvedValue(
      sessionDetail("conv-draft", "New conversation"),
    );
    vi.spyOn(window, "prompt").mockImplementation(() => null);
    vi.spyOn(window, "confirm").mockImplementation(() => true);
  });

  it("renders a local draft immediately and shows history loading in the sidebar", async () => {
    let resolveHistory: (value: PlaygroundSessionSummary[]) => void = () => undefined;
    playgroundApiMocks.listPlaygroundSessions.mockImplementationOnce(
      async () => await new Promise<PlaygroundSessionSummary[]>((resolve) => {
        resolveHistory = resolve;
      }),
    );

    renderChatPlayground();

    expect(await screen.findByRole("heading", { name: "New conversation" })).toBeVisible();
    expect(screen.getByText("Loading saved conversations...")).toBeVisible();
    expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled();
    expect(playgroundApiMocks.getPlaygroundSession).not.toHaveBeenCalled();

    resolveHistory([sessionSummary("conv-1", "Thread one")]);
    expect(await screen.findByRole("button", { name: /^Thread one/i })).toBeVisible();
  });

  it("collapses the history into a slim rail and restores the persisted collapsed state", async () => {
    const firstRender = renderChatPlayground();

    await waitForDraftReady();
    expect(await screen.findByRole("button", { name: /^Thread one/i })).toBeVisible();
    expect(getChatShell(firstRender.container)).toHaveAttribute("data-history-collapsed", "false");

    await userEvent.click(screen.getByRole("button", { name: "Collapse conversation history" }));

    expect(getChatShell(firstRender.container)).toHaveAttribute("data-history-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand conversation history" })).toBeVisible();
    expect(screen.getByRole("button", { name: "New chat" })).toBeVisible();
    expect(screen.queryByText("Choose a model and continue any prior conversation.")).toBeNull();
    expect(screen.queryByRole("button", { name: /^Thread one/i })).toBeNull();

    firstRender.unmount();

    const secondRender = renderChatPlayground();

    await waitForDraftReady();
    expect(getChatShell(secondRender.container)).toHaveAttribute("data-history-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand conversation history" })).toBeVisible();
  });

  it("shows model-loading UI instead of an empty-model state while chat models are still loading", async () => {
    let resolveModels: (value: { assistants: []; models: Array<{ id: string; display_name: string }> }) => void = () => undefined;
    playgroundApiMocks.getPlaygroundModelOptions.mockImplementationOnce(
      async () => await new Promise((resolve) => {
        resolveModels = resolve;
      }),
    );

    renderChatPlayground();

    expect(await screen.findByText("Loading available models...")).toBeVisible();
    expect(screen.getByLabelText("Model")).toHaveDisplayValue("Loading models...");
    expect(screen.queryByText("No enabled models")).toBeNull();

    resolveModels({
      assistants: [],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
    });

    await waitFor(() => expect(screen.getByLabelText("Model")).toHaveDisplayValue("Safe Small"));
    expect(screen.queryByText("Loading available models...")).toBeNull();
  });

  it("surfaces an honest unavailable-model state when no enabled models are returned", async () => {
    playgroundApiMocks.getPlaygroundModelOptions.mockResolvedValueOnce({
      assistants: [],
      models: [],
    });

    renderChatPlayground();

    expect(await screen.findByText("No enabled models are available right now.")).toBeVisible();
    expect(screen.getByLabelText("Model")).toHaveDisplayValue("No enabled models");
    expect(screen.getByLabelText("Message")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("updates draft selector state locally and creates a saved session only on the first send", async () => {
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-draft", "Test prompt", {
          model_selection: { model_id: "safe-large" },
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Test prompt",
        "## hello\n\nUse `code`",
      ),
    );

    renderChatPlayground();

    await waitForDraftReady();
    await userEvent.selectOptions(screen.getByLabelText("Model"), "safe-large");
    expect(playgroundApiMocks.updatePlaygroundSession).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText("Message"), "Test prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
      {
        playground_kind: "chat",
        assistant_ref: "assistant.playground.chat",
        model_selection: { model_id: "safe-large" },
        knowledge_binding: { knowledge_base_id: null },
      },
      "token",
    ));
    expect(playgroundApiMocks.streamPlaygroundMessage).toHaveBeenCalledWith(
      "conv-draft",
      { prompt: "Test prompt" },
      "token",
      expect.any(Object),
    );
    await waitFor(() => {
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("## hello");
      expect(screen.getByTestId("markdown-message")).toHaveTextContent("Use `code`");
    });
  });

  it("keeps user messages as plain text while rendering assistant markdown after persisting the draft", async () => {
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-draft", "Literal user", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:01Z",
        }),
        "**literal user**",
        "Answer with **bold**",
      ),
    );

    renderChatPlayground();

    await waitForDraftReady();
    await userEvent.type(screen.getByLabelText("Message"), "**literal user**");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("**literal user**")).toBeVisible();
    expect(await screen.findByTestId("markdown-message")).toHaveTextContent("Answer with **bold**");
  });

  it("moves rename and delete into the row menu and keeps the main header clean", async () => {
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

    await openSavedChat();
    expect(await screen.findByRole("button", { name: /^Thread two/i })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Thread one" }));
    expect(screen.getByRole("menuitem", { name: "Rename" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Delete" })).toBeVisible();
    await userEvent.click(screen.getByRole("menuitem", { name: "Rename" }));
    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "conv-1",
      { title: "Renamed thread" },
      "token",
    ));
    expect(await screen.findByRole("heading", { name: "Renamed thread" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Renamed thread" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(playgroundApiMocks.deletePlaygroundSession).toHaveBeenCalledWith("conv-1", "token");
    await waitFor(() => expect(screen.queryByRole("button", { name: /^Renamed thread/i })).toBeNull());
    expect(playgroundApiMocks.getPlaygroundSession).toHaveBeenLastCalledWith("conv-2", "chat", "token");
  });

  it("switches back to a fresh local draft when New chat is clicked from a saved session", async () => {
    renderChatPlayground();

    await openSavedChat();
    expect(await screen.findByRole("heading", { name: "Thread one" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "New chat" }));

    expect(await screen.findByRole("heading", { name: "New conversation" })).toBeVisible();
    expect(playgroundApiMocks.createPlaygroundSession).not.toHaveBeenCalled();
  });

  it("renders a sidebar history error without blocking the local draft", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockRejectedValueOnce(new Error("History failed"));

    renderChatPlayground();

    expect(await screen.findByRole("heading", { name: "New conversation" })).toBeVisible();
    expect(await screen.findByText("History failed")).toBeVisible();
    expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled();
    await waitFor(() => expect(screen.getByLabelText("Message")).toBeEnabled());
  });

  it("autoscrolls on send and when switching from the draft to a saved session", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      sessionSummary("conv-1", "Thread one", { message_count: 2, updated_at: "2026-03-18T11:00:02Z" }),
      sessionSummary("conv-2", "Thread two", { message_count: 2, updated_at: "2026-03-18T11:00:01Z" }),
    ]);
    playgroundApiMocks.getPlaygroundSession
      .mockResolvedValueOnce(sessionDetail("conv-2", "Thread two", {
        message_count: 2,
        messages: [
          { id: "msg-2", role: "assistant", content: "Second thread", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
        ],
      }));
    playgroundApiMocks.streamPlaygroundMessage.mockResolvedValueOnce(
      sendResult(
        sessionSummary("conv-draft", "Fresh send", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:03Z",
        }),
        "Fresh send",
        "response",
      ),
    );

    const { container } = renderChatPlayground();
    await waitForDraftReady();

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

    await userEvent.click(screen.getByRole("button", { name: /^Thread two/i }));
    await screen.findByText("Second thread");
    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
  });

  it("restores the draft and cleans up the empty saved session when the first stream fails", async () => {
    playgroundApiMocks.streamPlaygroundMessage.mockRejectedValueOnce(new Error("Stream failed"));

    renderChatPlayground();

    await waitForDraftReady();
    await userEvent.type(screen.getByLabelText("Message"), "Broken prompt");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByLabelText("Message")).toHaveValue("Broken prompt"));
    expect(playgroundApiMocks.deletePlaygroundSession).toHaveBeenCalledWith("conv-draft", "token");
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

    await waitForDraftReady();
    await userEvent.type(screen.getByLabelText("Message"), "Lock controls");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "New chat" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Conversation actions for Thread one" })).toBeDisabled();
      expect(screen.getByRole("combobox", { name: "Model" })).toBeDisabled();
      expect(screen.getByRole("button", { name: /^Thread one/i })).toBeDisabled();
    });

    resolveStream(
      sendResult(
        sessionSummary("conv-draft", "Lock controls", {
          message_count: 2,
          updated_at: "2026-03-18T11:00:02Z",
        }),
        "Lock controls",
        "done",
      ),
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled());
  });

  it("truncates long saved titles to one row while preserving the full title in a tooltip", async () => {
    const longTitle = "This is a very long saved conversation title that should truncate in the history row";
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      sessionSummary("conv-1", longTitle, { updated_at: "2026-03-18T11:00:02Z" }),
    ]);

    renderChatPlayground();

    const title = await screen.findByText(longTitle);
    expect(title).toHaveClass("chatbot-conversation-item-title");
    expect(title).toHaveAttribute("title", longTitle);
  });

  it("closes the conversation row menu on outside click and when another row menu opens", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValueOnce([
      sessionSummary("conv-1", "Thread one", { updated_at: "2026-03-18T11:00:02Z" }),
      sessionSummary("conv-2", "Thread two", { updated_at: "2026-03-18T11:00:01Z" }),
    ]);

    renderChatPlayground();

    await screen.findByRole("button", { name: /^Thread one/i });
    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Thread one" }));
    expect(screen.getByRole("menuitem", { name: "Rename" })).toBeVisible();

    await userEvent.click(document.body);
    await waitFor(() => expect(screen.queryByRole("menuitem", { name: "Rename" })).toBeNull());

    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Thread one" }));
    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Thread two" }));
    expect(screen.getByRole("button", { name: "Conversation actions for Thread two" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Conversation actions for Thread one" })).toHaveAttribute("aria-expanded", "false");
  });
});
