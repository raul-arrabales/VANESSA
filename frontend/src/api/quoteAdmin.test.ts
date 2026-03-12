import { beforeEach, describe, expect, it, vi } from "vitest";
import { createQuote, fetchQuoteSummary } from "./quoteAdmin";

describe("quoteAdmin api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the shared authenticated request helper for summary", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        summary: {
          total: 2,
          active: 2,
          approved: 1,
          by_language: [],
          by_tone: [],
          by_origin: [],
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchQuoteSummary("token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/quotes/summary",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
  });

  it("sends create payloads as JSON through the shared helper", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        quote: {
          id: 1,
          language: "en",
          text: "Quote",
          author: "Author",
          source_universe: "Original",
          tone: "reflective",
          tags: [],
          is_active: true,
          is_approved: true,
          origin: "local",
          external_ref: null,
          created_at: null,
          updated_at: null,
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await createQuote({
      language: "en",
      text: "Quote",
      author: "Author",
      source_universe: "Original",
      tone: "reflective",
      tags: [],
      is_active: true,
      is_approved: true,
      origin: "local",
      external_ref: "",
    }, "token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/quotes",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer token",
        }),
      }),
    );
  });
});
