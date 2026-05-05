import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlaygroundSessionDetail, PlaygroundSessionSummary } from "../api/playgrounds";
import type { AuthUser } from "../auth/types";
import KnowledgePlaygroundPage from "../features/playgrounds/pages/KnowledgePlaygroundPage";
import { renderWithAppProviders } from "../test/renderWithAppProviders";

const playgroundApiMocks = vi.hoisted(() => ({
  getPlaygroundModelOptions: vi.fn(),
  getPlaygroundKnowledgeBaseOptions: vi.fn(),
  listPlaygroundSessions: vi.fn(),
  createPlaygroundSession: vi.fn(),
  getPlaygroundSession: vi.fn(),
  updatePlaygroundSession: vi.fn(),
  sendPlaygroundMessage: vi.fn(),
  deletePlaygroundSession: vi.fn(),
}));
const clipboardMocks = vi.hoisted(() => ({
  writeText: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/playgrounds", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/playgrounds")>();
  return {
    ...actual,
    getPlaygroundModelOptions: playgroundApiMocks.getPlaygroundModelOptions,
    getPlaygroundKnowledgeBaseOptions: playgroundApiMocks.getPlaygroundKnowledgeBaseOptions,
    listPlaygroundSessions: playgroundApiMocks.listPlaygroundSessions,
    createPlaygroundSession: playgroundApiMocks.createPlaygroundSession,
    getPlaygroundSession: playgroundApiMocks.getPlaygroundSession,
    updatePlaygroundSession: playgroundApiMocks.updatePlaygroundSession,
    deletePlaygroundSession: playgroundApiMocks.deletePlaygroundSession,
    sendPlaygroundMessage: playgroundApiMocks.sendPlaygroundMessage,
    streamPlaygroundMessage: vi.fn(),
  };
});

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

async function renderKnowledgeChat() {
  return await renderWithAppProviders(<KnowledgePlaygroundPage />);
}

function getKnowledgeShell(): HTMLElement {
  const shell = document.querySelector(".chatbot-shell");
  if (!(shell instanceof HTMLElement)) {
    throw new Error("Expected chatbot shell to be present");
  }
  return shell;
}

function summary(overrides: Partial<PlaygroundSessionSummary> = {}): PlaygroundSessionSummary {
  return {
    id: "sess-1",
    playground_kind: "knowledge",
    assistant_ref: "agent.knowledge_chat",
    title: "Knowledge session",
    title_source: "auto",
    model_selection: { model_id: "safe-small" },
    knowledge_binding: { knowledge_base_id: "kb_primary" },
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

async function openSavedSession(title = "Knowledge session"): Promise<void> {
  await userEvent.click(await screen.findByRole("button", { name: new RegExp(`^${title}`, "i") }));
}

async function openKnowledgeChatSettings(): Promise<void> {
  await userEvent.click(screen.getByRole("button", { name: "Chat settings" }));
}

async function closeKnowledgeChatSettings(): Promise<void> {
  await userEvent.click(screen.getByRole("button", { name: "Close" }));
}

describe("KnowledgePlaygroundPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    clipboardMocks.writeText.mockReset();
    clipboardMocks.writeText.mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: clipboardMocks.writeText,
      },
    });
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
          assistant_ref: "agent.knowledge_chat",
          display_name: "Knowledge Assistant",
          description: "Knowledge grounded",
          playground_kind: "knowledge",
          agent_id: "agent.knowledge_chat",
          knowledge_required: true,
        },
      ],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
    });
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValue({
      knowledge_bases: [
        {
          id: "kb_primary",
          display_name: "Product Docs",
          index_name: "kb_product_docs",
          is_default: true,
        },
      ],
      default_knowledge_base_id: "kb_primary",
      selection_required: false,
      configuration_message: null,
    });
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValue([summary()]);
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue(detail());
    playgroundApiMocks.createPlaygroundSession.mockResolvedValue(
      detail({
        id: "sess-draft",
        title: "Knowledge playground",
      }),
    );
  });

  it("sends knowledge-playground requests through a draft-backed session without preloading saved history", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
        id: "sess-draft",
        title: "First question",
        message_count: 2,
        messages: [
          { id: "m1", role: "user", content: "First question", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
          { id: "m2", role: "assistant", content: "answer", metadata: { sources: [] }, createdAt: "2026-03-18T11:00:01Z" },
        ],
      }),
      messages: [],
      output: "answer",
      retrieval: { index: "knowledge_base", result_count: 0 },
      sources: [],
    });

    await renderKnowledgeChat();

    expect(playgroundApiMocks.getPlaygroundSession).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Knowledge base")).toBeNull();
    await openKnowledgeChatSettings();
    expect(await screen.findByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await closeKnowledgeChatSettings();

    await userEvent.type(screen.getByLabelText("Message"), "First question");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    await waitFor(() => expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
      {
        playground_kind: "knowledge",
        assistant_ref: "agent.knowledge_chat",
        model_selection: { model_id: "safe-small" },
        knowledge_binding: { knowledge_base_id: "kb_primary" },
      },
      "token",
    ));
    await waitFor(() => expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenCalledTimes(1));
    expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenLastCalledWith("sess-draft", { prompt: "First question" }, "token");
  });

  it("waits for knowledge-base options after models load and shows a KB-specific loading message", async () => {
    let resolveKnowledgeBases: (value: {
      knowledge_bases: Array<{ id: string; display_name: string; index_name: string; is_default: boolean }>;
      default_knowledge_base_id: string | null;
      selection_required: boolean;
      configuration_message: null;
    }) => void = () => undefined;
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockImplementationOnce(
      async () => await new Promise((resolve) => {
        resolveKnowledgeBases = resolve;
      }),
    );

    await renderKnowledgeChat();

    expect(await screen.findByText("Loading knowledge bases...")).toBeVisible();
    await openKnowledgeChatSettings();
    expect(screen.getByLabelText("Model")).toHaveDisplayValue("Safe Small");
    expect(screen.getByLabelText("Knowledge base")).toHaveDisplayValue("Loading knowledge bases...");
    expect(screen.getByRole("button", { name: "Ask knowledge chat" })).toBeDisabled();

    resolveKnowledgeBases({
      knowledge_bases: [
        { id: "kb_primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: true },
      ],
      default_knowledge_base_id: "kb_primary",
      selection_required: false,
      configuration_message: null,
    });

    await waitFor(() => expect(screen.getByLabelText("Knowledge base")).toHaveValue("kb_primary"));
  });

  it("collapses the knowledge history into a slim rail while keeping the new-session control available", async () => {
    await renderKnowledgeChat();

    expect(screen.getByRole("button", { name: "Chat settings" })).toBeVisible();
    await openKnowledgeChatSettings();
    expect(await screen.findByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await closeKnowledgeChatSettings();
    expect(getKnowledgeShell()).toHaveAttribute("data-history-collapsed", "false");

    await userEvent.click(screen.getByRole("button", { name: "Collapse conversation history" }));

    expect(getKnowledgeShell()).toHaveAttribute("data-history-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand conversation history" })).toBeVisible();
    expect(screen.getByRole("button", { name: "New chat" })).toBeVisible();
    expect(screen.queryByText("Ground answers in a bound knowledge base and continue prior sessions.")).toBeNull();
    expect(screen.queryByRole("button", { name: /Knowledge session/ })).toBeNull();
  });

  it("opens custom conversation dialogs from the row menu without using browser-native prompts", async () => {
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValueOnce(
      summary({
        title: "Renamed knowledge chat",
      }),
    );

    await renderKnowledgeChat();

    await screen.findByRole("button", { name: /^Knowledge session/i });
    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Knowledge session" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Rename" }));

    expect(await screen.findByRole("dialog", { name: "Rename conversation" })).toBeVisible();
    expect(screen.getByLabelText("Conversation title")).toHaveValue("Knowledge session");
    await userEvent.clear(screen.getByLabelText("Conversation title"));
    await userEvent.type(screen.getByLabelText("Conversation title"), "Renamed knowledge chat");
    await userEvent.click(screen.getByRole("button", { name: "Save title" }));

    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "sess-1",
      { title: "Renamed knowledge chat" },
      "token",
    ));
    expect(await screen.findByRole("button", { name: /^Renamed knowledge chat/i })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Conversation actions for Renamed knowledge chat" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(await screen.findByRole("dialog", { name: "Delete conversation" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Delete conversation" })).toBeNull());
    expect(playgroundApiMocks.deletePlaygroundSession).not.toHaveBeenCalled();
  });

  it("shows the knowledge-base configuration blocker when no knowledge bases are available", async () => {
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValueOnce({
      knowledge_bases: [],
      default_knowledge_base_id: null,
      selection_required: false,
      configuration_message: "Knowledge bases are not configured.",
    });

    await renderKnowledgeChat();

    expect(await screen.findByText("Knowledge bases are not configured.")).toBeVisible();
    await openKnowledgeChatSettings();
    expect(screen.getByLabelText("Knowledge base")).toBeDisabled();
    await closeKnowledgeChatSettings();
    expect(screen.getByLabelText("Message")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Ask knowledge chat" })).toBeDisabled();
  });

  it("auto-heals legacy knowledge sessions with no KB binding after explicit resume", async () => {
    playgroundApiMocks.listPlaygroundSessions.mockResolvedValue([
      summary({
        knowledge_binding: { knowledge_base_id: null },
      }),
    ]);
    playgroundApiMocks.getPlaygroundSession.mockResolvedValue(
      detail({
        knowledge_binding: { knowledge_base_id: null },
      }),
    );
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValue(
      summary({
        knowledge_binding: { knowledge_base_id: "kb_primary" },
      }),
    );
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
        knowledge_binding: { knowledge_base_id: "kb_primary" },
        message_count: 2,
        messages: [
          { id: "m1", role: "user", content: "Legacy question", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
          { id: "m2", role: "assistant", content: "legacy answer", metadata: { sources: [] }, createdAt: "2026-03-18T11:00:01Z" },
        ],
      }),
      messages: [],
      output: "legacy answer",
      retrieval: { index: "knowledge_base", result_count: 0 },
      sources: [],
    });

    await renderKnowledgeChat();
    await openSavedSession();

    await waitFor(() => expect(playgroundApiMocks.getPlaygroundSession).toHaveBeenCalledWith("sess-1", "knowledge", "token"));
    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "sess-1",
      { knowledge_binding: { knowledge_base_id: "kb_primary" } },
      "token",
    ));
    await openKnowledgeChatSettings();
    expect(await screen.findByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await closeKnowledgeChatSettings();

    await userEvent.type(screen.getByLabelText("Message"), "Legacy question");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    await waitFor(() => expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenCalledWith(
      "sess-1",
      { prompt: "Legacy question" },
      "token",
    ));
  });

  it("updates the knowledge-base selector through the canonical session API only after a saved session is selected", async () => {
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValue(
      summary({
        knowledge_binding: { knowledge_base_id: "kb_secondary" },
      }),
    );
    playgroundApiMocks.getPlaygroundModelOptions.mockResolvedValue({
      assistants: [],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
    });
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValue({
      knowledge_bases: [
        { id: "kb_primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: true },
        { id: "kb_secondary", display_name: "Policies", index_name: "kb_policies", is_default: false },
      ],
      default_knowledge_base_id: "kb_primary",
      selection_required: false,
      configuration_message: null,
    });

    await renderKnowledgeChat();
    await openKnowledgeChatSettings();
    expect(await screen.findByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await userEvent.selectOptions(screen.getByLabelText("Knowledge base"), "kb_secondary");
    expect(playgroundApiMocks.updatePlaygroundSession).not.toHaveBeenCalled();
    await closeKnowledgeChatSettings();

    await openSavedSession();
    await openKnowledgeChatSettings();
    await userEvent.selectOptions(await screen.findByLabelText("Knowledge base"), "kb_secondary");

    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "sess-1",
      { knowledge_binding: { knowledge_base_id: "kb_secondary" } },
      "token",
    ));
  });

  it("shows an honest empty selector state when no default KB is available on the local draft", async () => {
    playgroundApiMocks.getPlaygroundModelOptions.mockResolvedValue({
      assistants: [],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
    });
    playgroundApiMocks.getPlaygroundKnowledgeBaseOptions.mockResolvedValue({
      knowledge_bases: [
        { id: "kb_primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: false },
        { id: "kb_secondary", display_name: "Policies", index_name: "kb_policies", is_default: false },
      ],
      default_knowledge_base_id: null,
      selection_required: true,
      configuration_message: null,
    });

    await renderKnowledgeChat();

    await openKnowledgeChatSettings();
    const selector = await screen.findByLabelText("Knowledge base");
    expect(selector).toHaveValue("");
    expect(screen.getByRole("option", { name: "Select knowledge base" })).toBeVisible();
    await closeKnowledgeChatSettings();

    await userEvent.type(screen.getByLabelText("Message"), "Need an answer");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(screen.getByText("Knowledge base is required.")).toBeVisible();
    expect(playgroundApiMocks.createPlaygroundSession).not.toHaveBeenCalled();
    expect(playgroundApiMocks.sendPlaygroundMessage).not.toHaveBeenCalled();
  });

  it("renders citations from persisted assistant metadata after the first draft send", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
        id: "sess-draft",
        title: "How does retrieval work?",
        message_count: 2,
        messages: [
          { id: "m1", role: "user", content: "How does retrieval work?", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
          {
            id: "m2",
            role: "assistant",
            content: "knowledge answer",
            metadata: {
              sources: [
                {
                  id: "doc-1",
                  title: "Architecture Overview",
                  snippet: "Retrieval uses the shared knowledge corpus.",
                  score: 0.92,
                  score_kind: "similarity",
                  relevance_score: 0.92,
                  relevance_kind: "similarity",
                  metadata: {
                    source_name: "Docs folder",
                    ignored_empty: "",
                  },
                },
              ],
              references: [
                {
                  id: "ref-1",
                  citation_label: "[1]",
                  title: "Architecture Overview",
                  description: "Docs folder",
                  file_reference: "docs/architecture.pdf",
                  file_url: "/v1/playgrounds/knowledge-bases/kb_primary/documents/doc-1/source-file",
                  pages: [3],
                  source_ids: ["doc-1"],
                },
              ],
            },
            createdAt: "2026-03-18T11:00:01Z",
          },
        ],
      }),
      messages: [],
      output: "knowledge answer",
      retrieval: { index: "knowledge_base", result_count: 1 },
    });

    await renderKnowledgeChat();

    await openKnowledgeChatSettings();
    expect(await screen.findByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await closeKnowledgeChatSettings();
    await userEvent.type(screen.getByLabelText("Message"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByRole("button", { name: "References (1)" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Architecture Overview")).not.toBeInTheDocument();
    expect(screen.queryByText("Retrieval uses the shared knowledge corpus.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "References (1)" }));
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Docs folder")).toBeVisible();
    expect(screen.getByText("Pages 3")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "/api/v1/playgrounds/knowledge-bases/kb_primary/documents/doc-1/source-file#page=3",
    );
    expect(screen.queryByText(/Similarity/i)).not.toBeInTheDocument();
  });

  it("copies only the assistant answer text without including source cards", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
        id: "sess-draft",
        title: "How does retrieval work?",
        message_count: 2,
        messages: [
          { id: "m1", role: "user", content: "How does retrieval work?", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
          {
            id: "m2",
            role: "assistant",
            content: "knowledge answer",
            metadata: {
              sources: [
                {
                  id: "doc-1",
                  title: "Architecture Overview",
                  snippet: "Retrieval uses the shared knowledge corpus.",
                },
              ],
            },
            createdAt: "2026-03-18T11:00:01Z",
          },
        ],
      }),
      messages: [],
      output: "knowledge answer",
      retrieval: { index: "knowledge_base", result_count: 1 },
    });

    await renderKnowledgeChat();

    await userEvent.type(await screen.findByLabelText("Message"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByRole("button", { name: "References (1)" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Copy response" }));

    await waitFor(() => expect(clipboardMocks.writeText).toHaveBeenCalledWith("knowledge answer"));
  });

  it("renders assistant markdown in knowledge playground replies after persisting the draft", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
        id: "sess-draft",
        title: "Summarize the docs",
        message_count: 2,
        messages: [
          { id: "m1", role: "user", content: "Summarize the docs", metadata: {}, createdAt: "2026-03-18T11:00:00Z" },
          {
            id: "m2",
            role: "assistant",
            content: "### Findings\n\n- First item\n- Second item",
            metadata: { sources: [] },
            createdAt: "2026-03-18T11:00:01Z",
          },
        ],
      }),
      messages: [],
      output: "### Findings\n\n- First item\n- Second item",
      retrieval: { index: "knowledge_base", result_count: 0 },
    });

    await renderKnowledgeChat();

    await userEvent.type(await screen.findByLabelText("Message"), "Summarize the docs");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByRole("heading", { name: "Findings" })).toBeVisible();
    expect(screen.getByText("First item")).toBeVisible();
    expect(screen.getByText("Second item")).toBeVisible();
  });
});
