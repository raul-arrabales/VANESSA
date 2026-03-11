import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nextProvider } from "react-i18next";
import type { AuthUser } from "../auth/types";
import i18n from "../i18n";
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
  render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </I18nextProvider>,
  );
}

describe("HomePage quote of the day", () => {
  beforeEach(async () => {
    mockUser = null;
    vi.restoreAllMocks();
    window.localStorage.clear();
    await act(async () => {
      await i18n.changeLanguage("en");
    });
  });

  it("loads the quote for guests using the active UI language", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      json: async () => ({
        quote: {
          id: 1,
          text: "Stars need skeptics too.",
          author: "VANESSA Curated",
          source_universe: "Original",
          tone: "reflective",
          language: "en",
          date: "2026-03-11",
          origin: "local",
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await renderHomePage();

    expect(await screen.findByText("Stars need skeptics too.")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/v1/content/quote-of-the-day?lang=en"),
      expect.any(Object),
    );
  });

  it("refetches the quote after switching the UI language", async () => {
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
      await i18n.changeLanguage("es");
    });

    expect(await screen.findByText("La consola tambien piensa.")).toBeVisible();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/v1/content/quote-of-the-day?lang=es"),
        expect.any(Object),
      );
    });
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
    expect(screen.getByRole("link", { name: "Run backend diagnostics" })).toHaveAttribute("href", "/backend-health");
  });
});
