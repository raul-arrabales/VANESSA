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

vi.mock("../api/modelops", () => ({
  listEnabledModels: vi.fn(),
}));

const modelApi = await import("../api/modelops");

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

  it("loads the overview dashboard with first-level navigation", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: "Agent and tool catalog" })).toBeVisible();
    const topNav = screen.getByRole("navigation", { name: "Catalog control sections" });
    expect(within(topNav).getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(within(topNav).getByRole("link", { name: "Tools" })).toBeVisible();
    expect(within(topNav).getByRole("link", { name: "Agents" })).toBeVisible();
    expect(screen.getByText("Catalog areas")).toBeVisible();
    expect(screen.queryByRole("navigation", { name: "Tool catalog sections" })).not.toBeInTheDocument();
  });

  it("creates an agent from the create-agent view", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogAgents).mockResolvedValue([]);

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=agents&view=create" });

    const subNav = await screen.findByRole("navigation", { name: "Agent catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Create agent" })).toHaveAttribute("aria-current", "page");

    await user.type(screen.getByLabelText("Agent ID"), "agent.beta");
    await user.type(screen.getByLabelText("Name"), "Agent Beta");
    await user.type(screen.getByLabelText("Description"), "Catalog agent");
    await user.type(screen.getByLabelText("Instructions"), "Use tools carefully.");
    await user.click(screen.getByRole("button", { name: "Create agent" }));

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

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=tools" });

    const subNav = await screen.findByRole("navigation", { name: "Tool catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Platform tools" })).toHaveAttribute("aria-current", "page");

    await user.click(await screen.findByRole("button", { name: "Validate" }));

    await waitFor(() => {
      expect(catalogApi.validateCatalogTool).toHaveBeenCalledWith("tool.web_search", "token");
    });
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("MCP gateway does not expose tool 'web_search'.")).toBeVisible();
  });

  it("opens the edit flow from the tools directory", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=tools" });

    await user.click(await screen.findByRole("button", { name: "Edit" }));

    expect(await screen.findByRole("heading", { name: "Create tool" })).toBeVisible();
    expect(screen.getByLabelText("Tool ID")).toHaveValue("tool.web_search");
    const subNav = screen.getByRole("navigation", { name: "Tool catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Create tool" })).toHaveAttribute("aria-current", "page");
  });
});
