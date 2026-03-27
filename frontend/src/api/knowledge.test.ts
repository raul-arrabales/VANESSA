import { describe, expect, it, vi } from "vitest";
import { listKnowledgeChatKnowledgeBases, runKnowledgeChat } from "./knowledge";

const playgroundApiMocks = vi.hoisted(() => ({
  createPlaygroundSession: vi.fn(),
  sendPlaygroundMessage: vi.fn(),
  getPlaygroundOptions: vi.fn(),
}));

vi.mock("./playgrounds", () => ({
  createPlaygroundSession: playgroundApiMocks.createPlaygroundSession,
  sendPlaygroundMessage: playgroundApiMocks.sendPlaygroundMessage,
  getPlaygroundOptions: playgroundApiMocks.getPlaygroundOptions,
}));

describe("knowledge api compatibility helpers", () => {
  it("runs knowledge chat via the canonical playground session flow", async () => {
    playgroundApiMocks.createPlaygroundSession.mockResolvedValue({
      id: "sess-1",
      knowledge_binding: { knowledge_base_id: "kb-primary" },
    });
    playgroundApiMocks.sendPlaygroundMessage.mockResolvedValue({
      session: { knowledge_binding: { knowledge_base_id: "kb-primary" } },
      output: "answer",
      response: { id: "exec-knowledge" },
      sources: [{ id: "doc-1", title: "Doc 1", snippet: "Snippet", metadata: {} }],
      retrieval: { index: "knowledge_base", result_count: 1 },
    });

    const payload = await runKnowledgeChat({ prompt: "hello", model: "safe-small" }, "token");

    expect(playgroundApiMocks.createPlaygroundSession).toHaveBeenCalledWith(
      {
        playground_kind: "knowledge",
        model_selection: { model_id: "safe-small" },
        knowledge_binding: { knowledge_base_id: null },
      },
      "token",
    );
    expect(playgroundApiMocks.sendPlaygroundMessage).toHaveBeenCalledWith("sess-1", { prompt: "hello" }, "token");
    expect(payload.output).toBe("answer");
    expect(payload.sources[0].title).toBe("Doc 1");
  });

  it("returns knowledge base options from playground configuration", async () => {
    playgroundApiMocks.getPlaygroundOptions.mockResolvedValue({
      assistants: [],
      models: [],
      knowledge_bases: [{ id: "kb-primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: true }],
      default_knowledge_base_id: "kb-primary",
      selection_required: false,
      configuration_message: null,
    });

    const payload = await listKnowledgeChatKnowledgeBases("token");

    expect(payload.default_knowledge_base_id).toBe("kb-primary");
    expect(payload.knowledge_bases[0].display_name).toBe("Product Docs");
  });
});
