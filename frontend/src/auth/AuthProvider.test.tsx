import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthProvider";
import { AUTH_TOKEN_STORAGE_KEY, AUTH_USER_STORAGE_KEY } from "./storage";
import type { AuthUser } from "./types";

const mockLoginUser = vi.fn();
const mockLogoutUser = vi.fn();
const mockFetchMe = vi.fn();
const mockRegisterUser = vi.fn();
const mockActivateUser = vi.fn();

vi.mock("./authApi", () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  loginUser: (...args: unknown[]) => mockLoginUser(...args),
  logoutUser: (...args: unknown[]) => mockLogoutUser(...args),
  fetchMe: (...args: unknown[]) => mockFetchMe(...args),
  registerUser: (...args: unknown[]) => mockRegisterUser(...args),
  activateUser: (...args: unknown[]) => mockActivateUser(...args),
}));

function TestConsumer(): JSX.Element {
  const { user, isAuthenticated, login, logout } = useAuth();

  return (
    <div>
      <p data-testid="is-auth">{isAuthenticated ? "yes" : "no"}</p>
      <p data-testid="username">{user?.username ?? "none"}</p>
      <button type="button" onClick={() => void login("admin", "secret")}>login</button>
      <button type="button" onClick={() => void logout()}>logout</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    mockFetchMe.mockResolvedValue({ user: null });
    mockLogoutUser.mockResolvedValue({ logged_out: true });
  });

  it("updates auth state on login and logout", async () => {
    const user = userTemplate({ role: "admin" });
    mockFetchMe.mockResolvedValue({ user });
    mockLoginUser.mockResolvedValue({
      access_token: "token-123",
      token_type: "bearer",
      expires_in: 3600,
      user,
    });

    const actor = userEvent.setup();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    expect(screen.getByTestId("is-auth")).toHaveTextContent("no");

    await actor.click(screen.getByRole("button", { name: "login" }));

    await waitFor(() => {
      expect(screen.getByTestId("is-auth")).toHaveTextContent("yes");
    });
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe("token-123");
    expect(window.localStorage.getItem(AUTH_USER_STORAGE_KEY)).toContain("alice");

    await actor.click(screen.getByRole("button", { name: "logout" }));

    expect(screen.getByTestId("is-auth")).toHaveTextContent("no");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(AUTH_USER_STORAGE_KEY)).toBeNull();
  });

  it("loads stored auth and refreshes /auth/me", async () => {
    const user = userTemplate({ role: "user" });
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stored-token");
    window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
    mockFetchMe.mockResolvedValue({ user });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await screen.findByText("yes");
    expect(mockFetchMe).toHaveBeenCalledWith("stored-token");
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
  });
});

function userTemplate(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 1,
    email: "alice@example.com",
    username: "alice",
    role: "user",
    is_active: true,
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}
