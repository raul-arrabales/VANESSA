import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import TabbedWorkspaceLayout from "./TabbedWorkspaceLayout";

describe("TabbedWorkspaceLayout", () => {
  it("renders the shared header, tabs, actions, secondary navigation, and content", async () => {
    const view = await renderWithAppProviders(
      <TabbedWorkspaceLayout
        eyebrow="Workspace"
        title="Shared shell"
        description="Reusable tabbed layout"
        ariaLabel="Workspace navigation"
        tabs={[
          { id: "overview", label: "Overview", to: "/workspace", isActive: true },
          { id: "settings", label: "Settings", to: "/workspace/settings", isActive: false },
        ]}
        actions={<a href="/back">Back</a>}
        secondaryNavigation={<div className="workspace-secondary-nav-test">Subview nav</div>}
      >
        <p>workspace content</p>
      </TabbedWorkspaceLayout>,
      { route: "/workspace" },
    );

    expect(screen.getByRole("heading", { name: "Shared shell" }).closest(".tabbed-workspace-layout")).not.toBeNull();
    expect(screen.getByText("Workspace")).toBeVisible();
    expect(screen.getByText("Reusable tabbed layout")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back" })).toHaveAttribute("href", "/back");
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/workspace/settings");
    expect(screen.getByText("Subview nav")).toBeVisible();
    expect(view.container.querySelector(".tabbed-workspace-secondary-nav")).not.toBeNull();
    expect(screen.getByText("workspace content")).toBeVisible();
  });
});
