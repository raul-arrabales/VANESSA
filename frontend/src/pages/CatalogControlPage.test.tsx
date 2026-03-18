import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import CatalogControlPage from "./CatalogControlPage";
import * as catalogApi from "../api/catalog";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("../api/catalog", () => ({
  listCatalogAgents: vi.fn(),
  createCatalogAgent: vi.fn(),
  updateCatalogAgent: vi.fn(),
  validateCatalogAgent: vi.fn(),
  listCatalogTools: vi.fn(),
  createCatalogTool: vi.fn(),
  updateCatalogTool: vi.fn(),
  validateCatalogTool: vi.fn(),
}));

vi.mock("../api/models", () => ({
  listEnabledModels: vi.fn(),
}));

const modelApi = await import("../api/models");

const agentFixture = {
  id: "agent.alpha",
  entity: { id: "agent.alpha", type: "agent" as const, owner_user_id: 1, visibility: "private" as const },
  current_version: "v1",
  status: "draft",
  published: false,
  published_at: null,
  spec: {
    name: "Agent Alpha",
    description: "Agent description",
    instructions: "Be concise.",
    default_model_ref: "safe-small",
    tool_refs: ["tool.web_search"],
    runtime_constraints: { internet_required: true, sandbox_required: false },
  },
};

const toolFixture = {
  id: "tool.web_search",
  entity: { id: "tool.web_search", type: "tool" as const, owner_user_id: 1, visibility: "private" as const },
  current_version: "v1",
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    name: "Web search",
    description: "Tool description",
    transport: "mcp" as const,
    connection_profile_ref: "default" as const,
    tool_name: "web_search",
    input_schema: {},
    output_schema: {},
    safety_policy: {},
    offline_compatible: false,
  },
};

async function renderPage(): Promise<void> {
  await renderWithAppProviders(<CatalogControlPage />);
}

describe("CatalogControlPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    vi.mocked(catalogApi.listCatalogAgents).mockResolvedValue([agentFixture]);
    vi.mocked(catalogApi.listCatalogTools).mockResolvedValue([toolFixture]);
    vi.mocked(modelApi.listEnabledModels).mockResolvedValue([{ id: "safe-small", name: "Safe Small" }]);
    vi.mocked(catalogApi.createCatalogAgent).mockResolvedValue(agentFixture);
    vi.mocked(catalogApi.updateCatalogAgent).mockResolvedValue({ ...agentFixture, published: true });
    vi.mocked(catalogApi.validateCatalogAgent).mockResolvedValue({
      agent: agentFixture,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
        resolved_tools: [{ id: "tool.web_search", name: "Web search", transport: "mcp", offline_compatible: false }],
        derived_runtime_requirements: { internet_required: true, sandbox_required: false },
      },
    });
    vi.mocked(catalogApi.createCatalogTool).mockResolvedValue(toolFixture);
    vi.mocked(catalogApi.updateCatalogTool).mockResolvedValue(toolFixture);
    vi.mocked(catalogApi.validateCatalogTool).mockResolvedValue({
      tool: toolFixture,
      validation: {
        valid: false,
        errors: ["MCP gateway does not expose tool 'web_search'."],
        warnings: [],
        runtime_checks: { tool_discovered: false },
      },
    });
  });

  it("loads and renders agents and tools", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: "Agent and tool catalog" })).toBeVisible();
    expect(await screen.findByText("Agent Alpha")).toBeVisible();
    expect((await screen.findAllByText("Web search")).length).toBeGreaterThan(0);
  });

  it("creates an agent from the typed form", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogAgents).mockResolvedValue([]);

    await renderPage();

    const agentsHeading = await screen.findByRole("heading", { name: "Agents" });
    const agentsPanel = agentsHeading.closest("article");
    expect(agentsPanel).not.toBeNull();
    const agentScope = within(agentsPanel as HTMLElement);

    await user.type(agentScope.getByLabelText("Agent ID"), "agent.beta");
    await user.type(agentScope.getByLabelText("Name"), "Agent Beta");
    await user.type(agentScope.getByLabelText("Description"), "Catalog agent");
    await user.type(agentScope.getByLabelText("Instructions"), "Use tools carefully.");
    await user.click(agentScope.getByRole("button", { name: "Create agent" }));

    await waitFor(() => {
      expect(catalogApi.createCatalogAgent).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "agent.beta",
          name: "Agent Beta",
          publish: false,
        }),
        "token",
      );
    });
  });

  it("validates a tool and renders validation errors", async () => {
    const user = userEvent.setup();

    await renderPage();

    const validateButtons = await screen.findAllByRole("button", { name: "Validate" });
    await user.click(validateButtons[1]);

    await waitFor(() => {
      expect(catalogApi.validateCatalogTool).toHaveBeenCalledWith("tool.web_search", "token");
    });
    expect(await screen.findByText("MCP gateway does not expose tool 'web_search'.")).toBeVisible();
  });
});
