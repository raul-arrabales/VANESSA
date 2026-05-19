import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CatalogAgent, CatalogAgentValidation } from "../../../api/catalog";
import { expectNamedIconAction, expectNoGenericCompactActions } from "../../../test/compactRegistryAssertions";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import CatalogAgentsDirectory from "./CatalogAgentsDirectory";

const platformAgent: CatalogAgent = {
  id: "agent.knowledge_chat",
  entity: { id: "agent.knowledge_chat", type: "agent", owner_user_id: 1, visibility: "private" },
  agent_kind: "platform",
  is_platform_agent: true,
  current_version: "v1",
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    name: "Knowledge Chat",
    description: "Answers questions using internal knowledge.",
    instructions: "Use sources.",
    runtime_prompts: { retrieval_context: "" },
    default_model_ref: "safe-small",
    tool_refs: ["tool.web_search"],
    mcp_server_refs: ["web_search"],
    agent_domain: "default",
    runtime_constraints: { internet_required: true, sandbox_required: false },
  },
};

const userAgent: CatalogAgent = {
  ...platformAgent,
  id: "agent.alpha",
  entity: { id: "agent.alpha", type: "agent", owner_user_id: 2, visibility: "private" },
  agent_kind: "user",
  is_platform_agent: false,
  published: false,
  published_at: null,
  spec: {
    ...platformAgent.spec,
    name: "Agent Alpha",
    description: "User-owned assistant.",
    tool_refs: [],
    mcp_server_refs: [],
    runtime_constraints: { internet_required: false, sandbox_required: false },
  },
};

const validationResult: CatalogAgentValidation = {
  agent: platformAgent,
  validation: {
    valid: true,
    errors: [],
    warnings: [],
    resolved_tools: [{ id: "tool.web_search", name: "Web search", execution_backend: "mcp_gateway_web_search", offline_compatible: false }],
    resolved_mcp_servers: [{ id: "mcp.web_search", slug: "web_search", name: "Web search MCP", backing_tool_id: "tool.web_search", enabled: true }],
    derived_runtime_requirements: { internet_required: true, sandbox_required: false },
  },
};

describe("CatalogAgentsDirectory", () => {
  it("opens lifecycle graph modals from compact agent rows", async () => {
    const user = userEvent.setup();
    await renderWithAppProviders(
      <CatalogAgentsDirectory
        agents={[platformAgent, userAgent]}
        title="Agents"
        description="Agent directory"
        emptyMessage="No agents"
        validationResults={{ [platformAgent.id]: validationResult }}
        validatingAgentId=""
        deletingAgentId=""
        onEdit={vi.fn()}
        onValidate={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expectNamedIconAction("button", "View lifecycle for Knowledge Chat");
    expectNamedIconAction("button", "View lifecycle for Agent Alpha");
    expectNamedIconAction("button", "Edit Knowledge Chat");
    expectNamedIconAction("button", "Validate Knowledge Chat");
    expectNoGenericCompactActions(["View lifecycle", "Edit", "Validate", "Delete"]);

    await user.click(screen.getByRole("button", { name: "View lifecycle for Knowledge Chat" }));

    const dialog = await screen.findByRole("dialog", { name: "Agent lifecycle: Knowledge Chat" });
    expect(within(dialog).getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getByText("Current")).toBeVisible();
    expect(within(dialog).getByText("Kind")).toBeVisible();
    expect(within(dialog).getByText("Platform")).toBeVisible();
    expect(within(dialog).getByText("Published")).toBeVisible();
    expect(within(dialog).getByText("Valid")).toBeVisible();
    expect(within(dialog).getByText("safe-small")).toBeVisible();
    expect(within(dialog).getAllByText("1").length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText("Internet required")).toBeVisible();
    expect(within(dialog).getByText("No sandbox")).toBeVisible();
  });
});
