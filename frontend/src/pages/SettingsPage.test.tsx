import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

function renderSettings(initialPath = "/settings"): void {
  render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/settings" element={<SettingsPage />}>
            <Route path="design" element={<div>design-outlet</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockUser = {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };
  });

  it("renders language and theme controls on settings home for authenticated users", () => {
    renderSettings("/settings");

    expect(screen.getByRole("heading", { name: "settings.personalization.title" })).toBeVisible();
    expect(screen.getByLabelText("language.label")).toBeVisible();
    expect(screen.getByTestId("theme-toggle")).toBeVisible();
  });

  it("hides admin and superadmin sections for standard users", () => {
    renderSettings("/settings");
    expect(screen.queryByRole("heading", { name: "settings.admin.title" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "settings.superadmin.title" })).toBeNull();
  });

  it("shows admin and superadmin sections for superadmin users", () => {
    mockUser = {
      id: 2,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    renderSettings("/settings");

    expect(screen.getByRole("heading", { name: "settings.admin.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "settings.superadmin.title" })).toBeVisible();
  });

  it("renders nested outlet on /settings/design without overview cards", () => {
    renderSettings("/settings/design");

    expect(screen.getByText("design-outlet")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "settings.personalization.title" })).toBeNull();
    expect(screen.queryByLabelText("language.label")).toBeNull();
    expect(screen.queryByTestId("theme-toggle")).toBeNull();
  });
});
