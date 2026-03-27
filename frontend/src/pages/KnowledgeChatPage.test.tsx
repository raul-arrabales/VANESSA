import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlaygroundSessionDetail, PlaygroundSessionSummary } from "../api/playgrounds";
import type { AuthUser } from "../auth/types";
import KnowledgePlaygroundPage from "../features/playgrounds/pages/KnowledgePlaygroundPage";
import { renderWithAppProviders } from "../test/renderWithAppProviders";

const playgroundApiMocks = vi.hoisted(() => ({
  getPlaygroundOptions: vi.fn(),
  listPlaygroundSessions: vi.fn(),
  createPlaygroundSession: vi.fn(),
  getPlaygroundSession: vi.fn(),
  updatePlaygroundSession: vi.fn(),
  sendPlaygroundMessage: vi.fn(),
  deletePlaygroundSession: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/playgrounds", () => ({
  getPlaygroundOptions: playgroundApiMocks.getPlaygroundOptions,
  listPlaygroundSessions: playgroundApiMocks.listPlaygroundSessions,
  createPlaygroundSession: playgroundApiMocks.createPlaygroundSession,
  getPlaygroundSession: playgroundApiMocks.getPlaygroundSession,
  updatePlaygroundSession: playgroundApiMocks.updatePlaygroundSession,
  deletePlaygroundSession: playgroundApiMocks.deletePlaygroundSession,
  sendPlaygroundMessage: playgroundApiMocks.sendPlaygroundMessage,
  streamPlaygroundMessage: vi.fn(),
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

async function renderKnowledgeChat(): Promise<void> {
  await renderWithAppProviders(<KnowledgePlaygroundPage />);
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

describe("KnowledgePlaygroundPage", () => {
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
    playgroundApiMocks.getPlaygroundOptions.mockResolvedValue({
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
  });

  it("sends knowledge-playground requests through backend sessions", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
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

    await screen.findByLabelText("Model");
    await userEvent.type(screen.getByLabelText("Message"), "First question");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));
    await waitFor(() => expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenCalledTimes(1));

    expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenLastCalledWith("sess-1", { prompt: "First question" }, "token");
  });

  it("updates the knowledge-base selector through the canonical session API", async () => {
    playgroundApiMocks.updatePlaygroundSession.mockResolvedValue(
      summary({
        knowledge_binding: { knowledge_base_id: "kb_secondary" },
      }),
    );
    playgroundApiMocks.getPlaygroundOptions.mockResolvedValue({
      assistants: [],
      models: [{ id: "safe-small", display_name: "Safe Small" }],
      knowledge_bases: [
        { id: "kb_primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: true },
        { id: "kb_secondary", display_name: "Policies", index_name: "kb_policies", is_default: false },
      ],
      default_knowledge_base_id: "kb_primary",
      selection_required: false,
      configuration_message: null,
    });

    await renderKnowledgeChat();

    await screen.findByLabelText("Knowledge base");
    await userEvent.selectOptions(screen.getByLabelText("Knowledge base"), "kb_secondary");

    await waitFor(() => expect(playgroundApiMocks.updatePlaygroundSession).toHaveBeenCalledWith(
      "sess-1",
      { knowledge_binding: { knowledge_base_id: "kb_secondary" } },
      "token",
    ));
  });

  it("renders citations from persisted assistant metadata", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
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

    await screen.findByLabelText("Model");
    expect(screen.getByLabelText("Knowledge base")).toHaveValue("kb_primary");
    await userEvent.type(screen.getByLabelText("Message"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Retrieval uses the shared knowledge corpus.")).toBeVisible();
  });

  it("renders assistant markdown in knowledge playground replies", async () => {
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: detail({
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

    await screen.findByLabelText("Model");
    await userEvent.type(screen.getByLabelText("Message"), "Summarize the docs");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByRole("heading", { name: "Findings" })).toBeVisible();
    expect(screen.getByText("First item")).toBeVisible();
    expect(screen.getByText("Second item")).toBeVisible();
  });
});
