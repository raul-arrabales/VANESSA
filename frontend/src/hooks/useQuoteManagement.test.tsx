import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../auth/authApi";
import { useQuoteManagement } from "./useQuoteManagement";

const tMock = vi.hoisted(() => vi.fn((key: string) => key));
const quoteApiMocks = vi.hoisted(() => ({
  fetchQuoteSummary: vi.fn(),
  fetchQuotes: vi.fn(),
  fetchQuoteById: vi.fn(),
  createQuote: vi.fn(),
  updateQuote: vi.fn(),
}));

vi.mock("../api/quoteAdmin", () => ({
  fetchQuoteSummary: quoteApiMocks.fetchQuoteSummary,
  fetchQuotes: quoteApiMocks.fetchQuotes,
  fetchQuoteById: quoteApiMocks.fetchQuoteById,
  createQuote: quoteApiMocks.createQuote,
  updateQuote: quoteApiMocks.updateQuote,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: tMock,
  }),
}));

describe("useQuoteManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    quoteApiMocks.fetchQuoteSummary.mockResolvedValue({
      total: 2,
      active: 2,
      approved: 1,
      by_language: [],
      by_tone: [],
      by_origin: [],
    });
    quoteApiMocks.fetchQuotes.mockResolvedValue({
      items: [],
      page: 1,
      page_size: 10,
      total: 0,
      filters: {},
    });
    quoteApiMocks.fetchQuoteById.mockResolvedValue({
      id: 10,
      language: "en",
      text: "Quote A",
      author: "Author A",
      source_universe: "Original",
      tone: "reflective",
      tags: ["ops"],
      is_active: true,
      is_approved: true,
      origin: "local",
      external_ref: null,
      created_at: null,
      updated_at: null,
    });
  });

  it("loads summary and list state on mount", async () => {
    const { result } = renderHook(() => useQuoteManagement("token"));

    await waitFor(() => {
      expect(result.current.isLoadingSummary).toBe(false);
      expect(result.current.isLoadingList).toBe(false);
    });

    expect(quoteApiMocks.fetchQuoteSummary).toHaveBeenCalledWith("token");
    expect(quoteApiMocks.fetchQuotes).toHaveBeenCalledWith("token", 1, 10, {});
  });

  it("opens and closes the create modal", async () => {
    const { result } = renderHook(() => useQuoteManagement("token"));

    await waitFor(() => {
      expect(result.current.isLoadingList).toBe(false);
    });

    act(() => {
      result.current.beginCreate();
    });
    expect(result.current.isEditorOpen).toBe(true);
    expect(result.current.isCreating).toBe(true);

    act(() => {
      result.current.closeEditor();
    });
    expect(result.current.isEditorOpen).toBe(false);
    expect(result.current.isCreating).toBe(false);
  });

  it("handles list loading failures", async () => {
    quoteApiMocks.fetchQuotes.mockRejectedValueOnce(new ApiError("broken list", 500));

    const { result } = renderHook(() => useQuoteManagement("token"));

    await waitFor(() => {
      expect(result.current.error).toBe("broken list");
    });
  });
});
