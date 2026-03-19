import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../auth/authApi";
import { runKnowledgeChat } from "./knowledge";

describe("runKnowledgeChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("posts knowledge chat requests and returns citations", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          output: "answer",
          response: { id: "exec-knowledge" },
          sources: [{ id: "doc-1", title: "Doc 1", snippet: "Snippet", metadata: {} }],
          retrieval: { index: "knowledge_base", result_count: 1 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const payload = await runKnowledgeChat({ prompt: "hello", model: "safe-small" }, "token");

    expect(payload.output).toBe("answer");
    expect(payload.sources[0].title).toBe("Doc 1");
  });

  it("throws ApiError on backend failures", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ error: "invalid_prompt", message: "prompt is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(runKnowledgeChat({ prompt: "", model: "safe-small" }, "token")).rejects.toBeInstanceOf(ApiError);
  });

  it("throws a readable ApiError when the backend returns html on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        "<!doctype html><html><body>server error</body></html>",
        { status: 500, headers: { "Content-Type": "text/html" } },
      ),
    );

    await expect(runKnowledgeChat({ prompt: "hello", model: "safe-small" }, "token")).rejects.toMatchObject({
      message: "Knowledge chat request failed: HTTP 500",
      status: 500,
    });
  });
});
