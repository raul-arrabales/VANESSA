import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { RequireAuth, RequireRole } from "./RouteGuards";
import type { AuthUser } from "./types";

let mockAuthState: {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
} = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
};

vi.mock("./AuthProvider", () => ({
  useAuth: () => ({
    ...mockAuthState,
    token: "",
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
    activatePendingUser: vi.fn(),
  }),
}));

describe("RouteGuards", () => {
  it("redirects unauthenticated users to /login", async () => {
    mockAuthState = { user: null, isAuthenticated: false, isLoading: false };

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <Routes>
          <Route
            path="/settings"
            element={(
              <RequireAuth>
                <div>profile</div>
              </RequireAuth>
            )}
          />
          <Route path="/login" element={<div>login-page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("login-page")).toBeVisible();
  });

  it("shows forbidden content for insufficient role", () => {
    mockAuthState = {
      user: {
        id: 1,
        email: "u@example.com",
        username: "u",
        role: "user",
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
    };

    render(
      <MemoryRouter>
        <RequireRole role="admin">
          <div>admin-content</div>
        </RequireRole>
      </MemoryRouter>,
    );

    expect(screen.getByText("Forbidden")).toBeVisible();
    expect(screen.queryByText("admin-content")).toBeNull();
  });
});
