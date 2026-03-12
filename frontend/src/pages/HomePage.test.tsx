import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../auth/types";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { ensureTestI18n, testI18n } from "../test/testI18n";
import HomePage from "./HomePage";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
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

async function renderHomePage(): Promise<void> {
  await renderWithAppProviders(<HomePage />);
}

describe("HomePage quote of the day", () => {
  beforeEach(async () => {
    mockUser = null;
    vi.restoreAllMocks();
    window.localStorage.clear();
    await act(async () => {
      await ensureTestI18n();
      await testI18n.changeLanguage("en");
    });
  });

  it("does not load or show the quote for guests", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderHomePage();

    expect(screen.queryByRole("heading", { name: "Quote of the day" })).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refetches the quote after switching the UI language", async () => {
    mockUser = {
      id: 2,
      email: "pilot@example.com",
      username: "pilot",
      role: "user",
      is_active: true,
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const language = url.includes("lang=es") ? "es" : "en";
      return {
        ok: true,
        status: 200,
        json: async () => ({
          quote: {
            id: language === "es" ? 2 : 1,
            text: language === "es" ? "La consola tambien piensa." : "The console thinks too.",
            author: "VANESSA Curated",
            source_universe: "Original",
            tone: "funny",
            language,
            date: "2026-03-11",
            origin: "local",
          },
        }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderHomePage();
    expect(await screen.findByText("The console thinks too.")).toBeVisible();

    await act(async () => {
      await testI18n.changeLanguage("es");
    });

    expect(await screen.findByText("La consola tambien piensa.")).toBeVisible();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/v1/content/quote-of-the-day?lang=es&selection=daily"),
        expect.any(Object),
      );
    });
  });

  it("loads a new random quote when the refresh button is clicked", async () => {
    mockUser = {
      id: 2,
      email: "pilot@example.com",
      username: "pilot",
      role: "user",
      is_active: true,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          quote: {
            id: 1,
            text: "The console thinks too.",
            author: "VANESSA Curated",
            source_universe: "Original",
            tone: "funny",
            language: "en",
            date: "2026-03-11",
            origin: "local",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          quote: {
            id: 2,
            text: "A second signal arrives.",
            author: "VANESSA Curated",
            source_universe: "Original",
            tone: "reflective",
            language: "en",
            date: "2026-03-12",
            origin: "local",
          },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await renderHomePage();
    expect(await screen.findByText("The console thinks too.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "New quote" }));

    expect(await screen.findByText("A second signal arrives.")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/content/quote-of-the-day?lang=en&selection=random"),
      expect.any(Object),
    );
  });

  it("disables the refresh button while a quote request is in flight", async () => {
    mockUser = {
      id: 2,
      email: "pilot@example.com",
      username: "pilot",
      role: "user",
      is_active: true,
    };

    let resolveRefreshFetch: (value: {
      ok: boolean;
      status: number;
      json: () => Promise<{ quote: {
        id: number;
        text: string;
        author: string;
        source_universe: string;
        tone: string;
        language: string;
        date: string;
        origin: string;
      } }>;
    }) => void = () => {};

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          quote: {
            id: 1,
            text: "The console thinks too.",
            author: "VANESSA Curated",
            source_universe: "Original",
            tone: "funny",
            language: "en",
            date: "2026-03-11",
            origin: "local",
          },
        }),
      })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveRefreshFetch = resolve;
          }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await renderHomePage();

    const readyButton = await screen.findByRole("button", { name: "New quote" });
    await userEvent.click(readyButton);

    const refreshButton = await screen.findByRole("button", { name: "Loading..." });
    expect(refreshButton).toBeDisabled();

    resolveRefreshFetch({
      ok: true,
      status: 200,
      json: async () => ({
        quote: {
          id: 2,
          text: "A second signal arrives.",
          author: "VANESSA Curated",
          source_universe: "Original",
          tone: "reflective",
          language: "en",
          date: "2026-03-12",
          origin: "local",
        },
      }),
    });

    expect(await screen.findByRole("button", { name: "New quote" })).toBeEnabled();
  });

  it("shows the quote card for authenticated users and keeps actions available when quote loading fails", async () => {
    mockUser = {
      id: 5,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 503,
      })),
    );

    await renderHomePage();

    expect(await screen.findByText("Unable to load the quote of the day right now.")).toBeVisible();
    expect(screen.getByRole("link", { name: "View profile" })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: "Open control panel" })).toHaveAttribute("href", "/control");
    expect(screen.getByRole("link", { name: "Open AI chat" })).toHaveAttribute("href", "/ai/chat");
  });
});
