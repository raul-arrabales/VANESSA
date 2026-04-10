import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import PlatformPageLayout from "./PlatformPageLayout";

describe("PlatformPageLayout", () => {
  it("renders inside the shared tabbed workspace shell with actions and tabs", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/platform/providers"
          element={(
            <PlatformPageLayout
              title="Providers"
              description="Manage providers"
              actions={<button type="button">Create provider</button>}
            >
              <p>platform-child</p>
            </PlatformPageLayout>
          )}
        />
      </Routes>,
      { route: "/control/platform/providers" },
    );

    expect(screen.getByRole("heading", { name: "Providers" }).closest(".tabbed-workspace-layout")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Create provider" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Providers" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Deployments" })).toHaveAttribute("href", "/control/platform/deployments");
    expect(screen.getByText("platform-child")).toBeVisible();
  });
});
