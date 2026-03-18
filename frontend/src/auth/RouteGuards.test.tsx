import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { RequireAuth, RequireRole } from "./RouteGuards";
import type { AuthUser } from "./types";
import TestRouter from "../test/TestRouter";

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
      <TestRouter route="/settings">
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
      </TestRouter>,
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
      <TestRouter>
        <RequireRole role="admin">
          <div>admin-content</div>
        </RequireRole>
      </TestRouter>,
    );

    expect(screen.getByText("Forbidden")).toBeVisible();
    expect(screen.queryByText("admin-content")).toBeNull();
  });
});
