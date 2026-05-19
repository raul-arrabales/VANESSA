import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CatalogTool } from "../../../api/catalog";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { expectNamedIconAction, expectNoGenericCompactActions } from "../../../test/compactRegistryAssertions";
import CatalogToolsDirectory from "./CatalogToolsDirectory";

const readyTool: CatalogTool = {
  id: "tool.web_search",
  entity: { id: "tool.web_search", type: "tool", owner_user_id: 1, visibility: "private" },
  current_version: "v1",
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    name: "Web search",
    description: "Searches the public web.",
    input_schema: {},
    output_schema: {},
    safety_policy: {},
    offline_compatible: false,
    execution_backend: "mcp_gateway_web_search",
    execution_config: {},
    permissions: {},
  },
  validation_status: {
    last_validation_status: "success",
    is_validation_current: true,
    validated_version: "v1",
    last_validated_at: "2026-01-01T00:00:00+00:00",
    validation_errors: [],
  },
};

describe("CatalogToolsDirectory", () => {
  it("opens a lifecycle graph modal from compact tool rows", async () => {
    const user = userEvent.setup();
    await renderWithAppProviders(
      <CatalogToolsDirectory
        tools={[readyTool]}
        validationResults={{}}
        validatingToolId=""
        onEdit={vi.fn()}
        onTest={vi.fn()}
        onValidate={vi.fn()}
      />,
    );

    expectNamedIconAction("button", "View lifecycle for Web search");
    expectNamedIconAction("button", "Edit Web search");
    expectNamedIconAction("button", "Test Web search");
    expectNamedIconAction("button", "Validate Web search");
    expectNoGenericCompactActions(["View lifecycle", "Edit", "Test", "Validate"]);

    await user.click(screen.getByRole("button", { name: "View lifecycle for Web search" }));

    const dialog = await screen.findByRole("dialog", { name: "Tool lifecycle: Web search" });
    expect(within(dialog).getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getByText("Current")).toBeVisible();
    expect(within(dialog).getByText("Backend")).toBeVisible();
    expect(within(dialog).getByText("Gateway web search")).toBeVisible();
    expect(within(dialog).getByText("Published")).toBeVisible();
    expect(within(dialog).getByText("Success")).toBeVisible();
    expect(within(dialog).getByText("Network required")).toBeVisible();
  });
});
