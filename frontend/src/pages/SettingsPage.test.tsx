import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { AuthUser } from "../auth/types";
import SettingsPage from "./SettingsPage";
import TestRouter from "../test/TestRouter";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      resolvedLanguage: "en",
      changeLanguage: vi.fn(),
    },
  }),
}));

let mockUser: AuthUser | null = null;

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

vi.mock("../components/RuntimeProfileSection", () => ({
  default: () => <div>runtime-profile-section</div>,
}));

function renderSettings(initialPath = "/settings"): void {
  render(
    <ThemeProvider>
      <TestRouter route={initialPath}>
        <SettingsPage />
      </TestRouter>
    </ThemeProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };
  });

  it("renders profile and personalization only for standard users", async () => {
    renderSettings("/settings");

    expect(await screen.findByRole("heading", { name: "settings.profile.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "settings.personalization.language.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "settings.personalization.theme.title" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "settings.admin.title" })).toBeNull();
    expect(screen.queryByText("runtime-profile-section")).toBeNull();
    expect(screen.queryByRole("heading", { name: "settings.navigation.title" })).toBeNull();
    expect(screen.getByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
  });

  it("hides model and approvals controls for admins", async () => {
    mockUser = {
      id: 3,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    renderSettings("/settings");

    expect(await screen.findByRole("heading", { name: "settings.personalization.language.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "settings.personalization.theme.title" })).toBeVisible();
    expect(screen.getByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
    expect(screen.queryByText("runtime-profile-section")).toBeNull();
  });

  it("keeps canonical links for superadmin settings", async () => {
    mockUser = {
      id: 2,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    renderSettings("/settings");

    expect(await screen.findByRole("heading", { name: "settings.personalization.language.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "settings.personalization.theme.title" })).toBeVisible();
    expect(await screen.findByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
    expect(screen.queryByText("runtime-profile-section")).toBeNull();
    expect(screen.queryByRole("heading", { name: "settings.superadmin.title" })).toBeNull();
  });
});
