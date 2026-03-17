import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../auth/types";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import KnowledgeChatPage from "./KnowledgeChatPage";

const modelApiMocks = vi.hoisted(() => ({
  listEnabledModels: vi.fn(),
}));

const knowledgeApiMocks = vi.hoisted(() => ({
  runKnowledgeChat: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/models", () => ({
  listEnabledModels: modelApiMocks.listEnabledModels,
}));

vi.mock("../api/knowledge", () => ({
  runKnowledgeChat: knowledgeApiMocks.runKnowledgeChat,
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

function renderKnowledgeChat(): void {
  renderWithAppProviders(<KnowledgeChatPage />);
}

describe("KnowledgeChatPage", () => {
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

  it("sends knowledge-chat requests with prior context only", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValue([{ id: "safe-small", name: "Safe Small" }]);
    knowledgeApiMocks.runKnowledgeChat.mockResolvedValue({ output: "answer", sources: [], retrieval: { index: "knowledge_base", result_count: 0 } });

    renderKnowledgeChat();

    await screen.findByLabelText("Model");
    await userEvent.type(screen.getByLabelText("Message"), "First question");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));
    await waitFor(() => expect(knowledgeApiMocks.runKnowledgeChat).toHaveBeenCalledTimes(1));

    expect(knowledgeApiMocks.runKnowledgeChat).toHaveBeenLastCalledWith(
      {
        prompt: "First question",
        model: "safe-small",
        history: [],
      },
      "token",
    );
  });

  it("renders citations and keeps storage isolated from plain chat", async () => {
    modelApiMocks.listEnabledModels.mockResolvedValue([{ id: "safe-small", name: "Safe Small" }]);
    knowledgeApiMocks.runKnowledgeChat.mockResolvedValue({
      output: "knowledge answer",
      sources: [
        {
          id: "doc-1",
          title: "Architecture Overview",
          snippet: "Retrieval uses the shared knowledge corpus.",
          uri: null,
          metadata: {},
        },
      ],
      retrieval: { index: "knowledge_base", result_count: 1 },
    });

    renderKnowledgeChat();

    await screen.findByLabelText("Model");
    await userEvent.type(screen.getByLabelText("Message"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Ask knowledge chat" }));

    expect(await screen.findByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Retrieval uses the shared knowledge corpus.")).toBeVisible();
    expect(window.localStorage.getItem("vanessa:knowledge-chat:10")).toContain("knowledge answer");
    expect(window.localStorage.getItem("vanessa:chat:10")).toBeNull();
  });
});
