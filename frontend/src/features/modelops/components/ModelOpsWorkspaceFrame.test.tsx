import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { ModelOpsWorkspaceFrame } from "./ModelOpsWorkspaceFrame";

let mockRole: "user" | "admin" | "superadmin" = "user";

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "tester", email: "t@example.com", role: mockRole, is_active: true },
    token: "token",
    isAuthenticated: true,
  }),
}));

describe("ModelOpsWorkspaceFrame", () => {
  it("renders shared workspace tabs for regular users", async () => {
    mockRole = "user";

    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/models/catalog"
          element={
            <ModelOpsWorkspaceFrame>
              <p>workspace-child</p>
            </ModelOpsWorkspaceFrame>
          }
        />
      </Routes>,
      { route: "/control/models/catalog" },
    );

    expect(screen.getByRole("heading", { name: "ModelOps" })).toBeVisible();
    expect(screen.getByText("workspace-child")).toBeVisible();
    expect(screen.getByRole("heading", { name: "ModelOps" }).closest(".tabbed-workspace-layout")).not.toBeNull();
    expect(screen.getByRole("link", { name: "Models" })).toHaveAttribute("href", "/control/models");
    expect(screen.getByRole("link", { name: "Model catalog" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Register cloud model" })).toHaveAttribute("href", "/control/models/cloud/register");
    expect(screen.queryByRole("link", { name: "Model access" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Register local model" })).not.toBeInTheDocument();
  });

  it("shows admin and superadmin tabs according to role", async () => {
    mockRole = "superadmin";

    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/models/local/artifacts"
          element={
            <ModelOpsWorkspaceFrame>
              <p>workspace-child</p>
            </ModelOpsWorkspaceFrame>
          }
        />
      </Routes>,
      { route: "/control/models/local/artifacts" },
    );

    expect(screen.getByRole("link", { name: "Model access" })).toHaveAttribute("href", "/control/models/access");
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("href", "/control/models/local/register");
    expect(screen.getByRole("link", { name: "Local artifacts" })).toHaveAttribute("aria-current", "page");
  });
});
