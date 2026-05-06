import { afterEach, describe, expect, it, vi } from "vitest";
import { streamPlaygroundMessage } from "./playgrounds";

describe("playgrounds API streaming", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses status events from playground SSE streams", async () => {
    const body = [
      "event: status",
      'data: {"id":"thinking-1","kind":"thinking","label":"Thinking","state":"running"}',
      "",
      "event: complete",
      'data: {"session":{"id":"sess-1","playground_kind":"chat","assistant_ref":"assistant.playground.chat","title":"Chat","title_source":"auto","model_selection":{"model_id":"safe-small"},"knowledge_binding":{"knowledge_base_id":null},"message_count":2,"created_at":null,"updated_at":null,"messages":[]},"messages":[],"output":"done"}',
      "",
    ].join("\n") + "\n";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const onStatus = vi.fn();

    const result = await streamPlaygroundMessage(
      "sess-1",
      { prompt: "hello" },
      "token",
      { onStatus },
    );

    expect(onStatus).toHaveBeenCalledWith(expect.objectContaining({
      id: "thinking-1",
      kind: "thinking",
      label: "Thinking",
      state: "running",
    }));
    expect(result.output).toBe("done");
  });
});
