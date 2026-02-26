import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import SuperAdminWelcomePage from "./SuperAdminWelcomePage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "sample-superadmin@example.com",
      username: "sample-superadmin",
      role: "superadmin",
      is_active: true,
    },
  }),
}));

describe("SuperAdminWelcomePage", () => {
  it("renders full-card links and no per-tile action buttons", () => {
    const { container } = render(
      <MemoryRouter>
        <SuperAdminWelcomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("list", { name: "Superadmin available items" })).toBeVisible();
    expect(screen.getByRole("link", { name: "View your profile" })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: "Process user approvals" })).toHaveAttribute("href", "/admin/approvals");
    expect(screen.getByRole("link", { name: "Backend health" })).toHaveAttribute("href", "/backend-health");
    expect(screen.getByRole("link", { name: "models.title" })).toHaveAttribute("href", "/welcome/superadmin/models");
    expect(screen.getByRole("link", { name: "Open user welcome page" })).toHaveAttribute("href", "/welcome/user");
    expect(screen.getByRole("link", { name: "Open admin welcome page" })).toHaveAttribute("href", "/welcome/admin");
    expect(screen.queryByRole("button", { name: /open/i })).toBeNull();
    expect(container.querySelectorAll(".option-card-icon svg")).toHaveLength(6);
  });
});
