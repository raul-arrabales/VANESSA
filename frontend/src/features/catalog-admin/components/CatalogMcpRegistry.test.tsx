import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CatalogMcpServer, CatalogTool } from "../../../api/catalog";
import { expectNamedIconAction, expectNoGenericCompactActions } from "../../../test/compactRegistryAssertions";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import CatalogMcpRegistry from "./CatalogMcpRegistry";

const tool: CatalogTool = {
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

const mcpServer: CatalogMcpServer = {
  id: "mcp.web_search",
  entity: { id: "mcp.web_search", type: "mcp_server", owner_user_id: 1, visibility: "private" },
  current_version: "v1",
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    name: "Web search MCP",
    slug: "web_search",
    description: "Expose web search through MCP.",
    backing_tool_id: "tool.web_search",
    exposed_tool_name: "web_search",
    input_schema: {},
    output_schema: {},
    metadata: {
      category: "web_search",
      capabilities: ["web-search"],
      local: false,
      stateless: true,
      sandboxed: false,
      risk_level: "medium",
      data_access: "public_web",
      output_freshness: "fresh",
      audit_level: "standard",
    },
    authorization_policy: {
      agent_ids: ["*"],
      agent_domains: ["*"],
      agent_roles: ["*"],
      user_roles: ["*"],
      user_ids: ["*"],
      user_group_ids: ["*"],
    },
    enabled: true,
  },
  validation_status: {
    last_validation_status: "success",
    is_validation_current: true,
    validated_version: "v1",
    last_validated_at: "2026-01-01T00:00:00+00:00",
    validation_errors: [],
  },
};

describe("CatalogMcpRegistry", () => {
  it("opens a lifecycle graph modal from compact MCP rows", async () => {
    const user = userEvent.setup();
    await renderWithAppProviders(
      <CatalogMcpRegistry
        mcpServers={[mcpServer]}
        tools={[tool]}
        validationResults={{}}
        validatingMcpServerId=""
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onToggle={vi.fn()}
        onValidate={vi.fn()}
      />,
    );

    expectNamedIconAction("button", "View lifecycle for Web search MCP");
    expectNamedIconAction("button", "View full description for Web search MCP");
    expectNamedIconAction("button", "Edit Web search MCP");
    expectNamedIconAction("button", "Disable Web search MCP");
    expectNamedIconAction("button", "Validate Web search MCP");
    expectNoGenericCompactActions(["View lifecycle", "Edit", "Disable", "Validate", "Delete"]);

    await user.click(screen.getByRole("button", { name: "View lifecycle for Web search MCP" }));

    const dialog = await screen.findByRole("dialog", { name: "MCP lifecycle: Web search MCP" });
    expect(within(dialog).getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getByText("Current")).toBeVisible();
    expect(within(dialog).getByText("Category")).toBeVisible();
    expect(within(dialog).getAllByText("Web search").length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText("Medium")).toBeVisible();
    expect(within(dialog).getByText("Enabled")).toBeVisible();
    expect(within(dialog).getByText("Success")).toBeVisible();
    expect(within(dialog).getByText("Network required")).toBeVisible();
    expect(within(dialog).getByText("Stateless")).toBeVisible();
    expect(within(dialog).getByText("Unsandboxed")).toBeVisible();
  });
});
