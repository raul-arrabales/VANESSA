import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import QuoteManagementPage from "./QuoteManagementPage";

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

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    token: "token",
  }),
}));

describe("QuoteManagementPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    quoteApiMocks.fetchQuoteSummary.mockResolvedValue({
      total: 2,
      active: 2,
      approved: 1,
      by_language: [{ value: "en", count: 2 }],
      by_tone: [{ value: "reflective", count: 1 }],
      by_origin: [{ value: "local", count: 2 }],
    });
    quoteApiMocks.fetchQuotes.mockResolvedValue({
      items: [{
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
        created_at: "2026-03-10T10:00:00+00:00",
        updated_at: "2026-03-12T10:00:00+00:00",
      }],
      page: 1,
      page_size: 10,
      total: 1,
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
      created_at: "2026-03-10T10:00:00+00:00",
      updated_at: "2026-03-12T10:00:00+00:00",
    });
  });

  function renderPage(): void {
    render(
      <MemoryRouter>
        <QuoteManagementPage />
      </MemoryRouter>,
    );
  }

  it("loads summary and quote list", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "quoteAdmin.title" })).toBeVisible();
    await waitFor(() => {
      expect(quoteApiMocks.fetchQuoteSummary).toHaveBeenCalledWith("token");
      expect(quoteApiMocks.fetchQuotes).toHaveBeenCalledWith("token", 1, 10, {});
      expect(screen.getAllByText("Quote A").length).toBeGreaterThan(0);
    });
  });

  it("searches and paginates results", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("heading", { name: "quoteAdmin.title" });
    await user.type(screen.getByLabelText("quoteAdmin.filters.source"), "Original");
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.search" }));

    await waitFor(() => {
      expect(quoteApiMocks.fetchQuotes).toHaveBeenLastCalledWith("token", 1, 10, { source_universe: "Original" });
    });
  });

  it("loads selected quote details and saves edits", async () => {
    const user = userEvent.setup();
    quoteApiMocks.updateQuote.mockResolvedValue({
      id: 10,
      language: "en",
      text: "Updated quote",
      author: "Author A",
      source_universe: "Original",
      tone: "reflective",
      tags: ["ops"],
      is_active: true,
      is_approved: true,
      origin: "local",
      external_ref: null,
      created_at: "2026-03-10T10:00:00+00:00",
      updated_at: "2026-03-12T11:00:00+00:00",
    });

    renderPage();
    await screen.findByText("Quote A");
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.edit" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(await screen.findByDisplayValue("Quote A")).toBeVisible();
    await user.clear(screen.getByLabelText("quoteAdmin.editor.fields.text"));
    await user.type(screen.getByLabelText("quoteAdmin.editor.fields.text"), "Updated quote");
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.save" }));

    await waitFor(() => {
      expect(quoteApiMocks.updateQuote).toHaveBeenCalledWith(10, expect.objectContaining({ text: "Updated quote" }), "token");
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("creates a new quote", async () => {
    const user = userEvent.setup();
    quoteApiMocks.createQuote.mockResolvedValue({
      id: 12,
      language: "en",
      text: "Brand new quote",
      author: "Curator",
      source_universe: "Original",
      tone: "funny",
      tags: ["new"],
      is_active: true,
      is_approved: true,
      origin: "local",
      external_ref: null,
      created_at: "2026-03-12T11:00:00+00:00",
      updated_at: "2026-03-12T11:00:00+00:00",
    });

    renderPage();
    await screen.findByRole("heading", { name: "quoteAdmin.title" });
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.new" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    await user.clear(screen.getByLabelText("quoteAdmin.editor.fields.author"));
    await user.type(screen.getByLabelText("quoteAdmin.editor.fields.author"), "Curator");
    await user.clear(screen.getByLabelText("quoteAdmin.editor.fields.text"));
    await user.type(screen.getByLabelText("quoteAdmin.editor.fields.text"), "Brand new quote");
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.save" }));

    await waitFor(() => {
      expect(quoteApiMocks.createQuote).toHaveBeenCalledWith(expect.objectContaining({
        author: "Curator",
        text: "Brand new quote",
      }), "token");
    });
  });

  it("closes the modal without saving when cancel is clicked", async () => {
    const user = userEvent.setup();

    renderPage();
    await screen.findByRole("heading", { name: "quoteAdmin.title" });
    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.new" }));
    expect(await screen.findByRole("dialog")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "quoteAdmin.actions.cancel" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(quoteApiMocks.createQuote).not.toHaveBeenCalled();
    expect(quoteApiMocks.updateQuote).not.toHaveBeenCalled();
  });
});
