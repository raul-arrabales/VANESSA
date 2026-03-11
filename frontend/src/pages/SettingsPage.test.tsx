import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { AuthUser } from "../auth/types";
import SettingsPage from "./SettingsPage";

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
    activatePendingUser: vi.fn(),
    listPendingUsers: vi.fn(),
    updateUserRole: vi.fn(),
  }),
}));

vi.mock("../components/RuntimeProfileSection", () => ({
  default: () => <div>runtime-profile-section</div>,
}));

function renderSettings(initialPath = "/settings"): void {
  render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <SettingsPage />
      </MemoryRouter>
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

    expect(await screen.findByRole("heading", { name: "settings.personalization.title" })).toBeVisible();
    expect(screen.getByText("runtime-profile-section")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "settings.admin.title" })).toBeNull();
    expect(screen.getByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
    expect(screen.getByRole("link", { name: "nav.models" })).toHaveAttribute("href", "/control/models");
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

    expect(await screen.findByRole("heading", { name: "settings.personalization.title" })).toBeVisible();
    expect(screen.getByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
    expect(screen.getByRole("link", { name: "nav.control" })).toHaveAttribute("href", "/control");
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

    expect(await screen.findByRole("link", { name: "settings.personalization.theme.styleEditor" })).toHaveAttribute("href", "/settings/design");
    expect(screen.getByRole("link", { name: "nav.models" })).toHaveAttribute("href", "/control/models");
    expect(screen.queryByRole("heading", { name: "settings.superadmin.title" })).toBeNull();
  });
});
