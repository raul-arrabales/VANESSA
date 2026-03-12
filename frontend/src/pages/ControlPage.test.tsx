import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../auth/types";
import ControlPage from "./ControlPage";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

function renderPage(): void {
  render(
    <MemoryRouter>
      <ControlPage />
    </MemoryRouter>,
  );
}

describe("ControlPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("hides the quotes control from regular users", () => {
    mockUser = {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    renderPage();

    expect(screen.queryByRole("link", { name: "control.items.quotes.title" })).toBeNull();
  });

  it("shows the quotes control for admin users", () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    renderPage();

    expect(screen.getByRole("link", { name: "control.items.quotes.title" })).toHaveAttribute("href", "/control/quotes");
  });
});
