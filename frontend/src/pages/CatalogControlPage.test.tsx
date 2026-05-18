import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { expectCompactRegistryRowForHeading, expectNamedIconAction, expectNoGenericCompactActions } from "../test/compactRegistryAssertions";
import type { AuthUser } from "../auth/types";
import type { CatalogToolCreationOptions } from "../api/catalog";
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
  getCatalogDefaults: vi.fn(),
  getCatalogToolCreationOptions: vi.fn(),
  getCatalogMcpCreationOptions: vi.fn(),
  listCatalogAgents: vi.fn(),
  createCatalogAgent: vi.fn(),
  updateCatalogAgent: vi.fn(),
  deleteCatalogAgent: vi.fn(),
  previewCatalogAgentPrompt: vi.fn(),
  validateCatalogAgent: vi.fn(),
  listCatalogTools: vi.fn(),
  createCatalogTool: vi.fn(),
  updateCatalogTool: vi.fn(),
  validateCatalogTool: vi.fn(),
  testCatalogTool: vi.fn(),
  listCatalogMcpServers: vi.fn(),
  createCatalogMcpServer: vi.fn(),
  updateCatalogMcpServer: vi.fn(),
  deleteCatalogMcpServer: vi.fn(),
  validateCatalogMcpServer: vi.fn(),
  toggleCatalogMcpServer: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listEnabledModels: vi.fn(),
}));

const modelApi = await import("../api/modelops");
const apiRetrievalDefault = "Use API-provided retrieval instructions.";

const agentFixture = {
  id: "agent.alpha",
  entity: { id: "agent.alpha", type: "agent" as const, owner_user_id: 1, visibility: "private" as const },
  agent_kind: "user" as const,
  is_platform_agent: false,
  current_version: "v1",
  status: "draft",
  published: false,
  published_at: null,
  spec: {
    name: "Agent Alpha",
    description: "Agent description",
    instructions: "Be concise.",
    runtime_prompts: {
      retrieval_context: "Use retrieved context and cite references.",
    },
    default_model_ref: "safe-small",
    tool_refs: ["tool.web_search"],
    runtime_constraints: { internet_required: true, sandbox_required: false },
  },
};

const platformAgentFixture = {
  ...agentFixture,
  id: "agent.knowledge_chat",
  entity: { id: "agent.knowledge_chat", type: "agent" as const, owner_user_id: 1, visibility: "private" as const },
  agent_kind: "platform" as const,
  is_platform_agent: true,
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    ...agentFixture.spec,
    name: "Knowledge Chat",
    description: "Product-facing knowledge-backed chat agent.",
    tool_refs: [],
    runtime_constraints: { internet_required: false, sandbox_required: false },
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
    execution_backend: "mcp_gateway_web_search" as const,
    execution_config: {},
    permissions: { scopes: [] },
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string" },
        top_k: { type: "integer", minimum: 1, maximum: 10 },
      },
      required: ["query"],
      additionalProperties: false,
    },
    output_schema: {},
    safety_policy: {},
    offline_compatible: false,
  },
  validation_status: {
    last_validation_status: "success",
    is_validation_current: true,
    validated_version: "v1",
    last_validated_at: "2026-01-01T00:00:00+00:00",
    validation_errors: [],
  },
};

const knowledgeBaseRetrievalTemplate = {
  id: "tool.kb_retrieval.product-docs",
  visibility: "private" as const,
  publish: false,
  name: "Product Docs Retrieval",
  description: "Retrieves relevant passages from Product Docs.",
  execution_backend: "knowledge_base_retrieval" as const,
  execution_config: {
    knowledge_base_id: "kb-product-docs",
    retrieval_defaults: {
      top_k: 5,
      search_method: "semantic",
      query_preprocessing: "none",
    },
  },
  permissions: {},
  input_schema: {
    type: "object",
    properties: {
      query_text: { type: "string" },
      top_k: { type: "integer", minimum: 1 },
      search_method: { type: "string", enum: ["semantic", "keyword", "hybrid"] },
      query_preprocessing: { type: "string", enum: ["none", "normalize"] },
      hybrid_alpha: { type: "number", minimum: 0, maximum: 1 },
      filters: { type: "object", additionalProperties: true },
    },
    required: ["query_text"],
    additionalProperties: false,
  },
  output_schema: {
    type: "object",
    properties: {
      knowledge_base_id: { type: "string" },
      retrieval: { type: "object", additionalProperties: true },
      results: { type: "array", items: { type: "object" } },
    },
    required: ["knowledge_base_id", "retrieval", "results"],
    additionalProperties: true,
  },
  safety_policy: { timeout_seconds: 8, network_access: false },
  offline_compatible: true,
};

const toolCreationOptionsFixture: CatalogToolCreationOptions = {
  execution_backends: [
    {
      execution_backend: "mcp_gateway_web_search" as const,
      requires_knowledge_base: false,
      template: {
        ...toolFixture.spec,
        id: "tool.custom_web_search",
        visibility: "private" as const,
        publish: false,
        name: "Web Search",
        description: "Searches the web through the MCP gateway's SearXNG-backed runner.",
      },
    },
    {
      execution_backend: "sandbox_python" as const,
      requires_knowledge_base: false,
      template: {
        id: "tool.custom_python_exec",
        visibility: "private" as const,
        publish: false,
        name: "Python Execution",
        description: "Runs constrained Python code in the sandbox runtime.",
        execution_backend: "sandbox_python" as const,
        execution_config: {},
        permissions: {},
        input_schema: { type: "object", properties: { code: { type: "string" } }, required: ["code"], additionalProperties: false },
        output_schema: { type: "object", additionalProperties: true },
        safety_policy: { timeout_seconds: 5, network_access: false },
        offline_compatible: true,
      },
    },
    {
      execution_backend: "knowledge_base_retrieval" as const,
      requires_knowledge_base: true,
      knowledge_bases: [
        {
          id: "kb-product-docs",
          display_name: "Product Docs",
          slug: "product-docs",
          index_name: "kb_product_docs",
          is_default: true,
        },
      ],
      templates_by_knowledge_base_id: {
        "kb-product-docs": knowledgeBaseRetrievalTemplate,
      },
    },
  ],
  knowledge_bases: [
    {
      id: "kb-product-docs",
      display_name: "Product Docs",
      slug: "product-docs",
      index_name: "kb_product_docs",
      is_default: true,
    },
  ],
  default_knowledge_base_id: "kb-product-docs",
  selection_required: false,
  configuration_message: null,
};

const kbRetrievalToolFixture = {
  ...toolFixture,
  id: "tool.kb_retrieval.product-docs",
  entity: { id: "tool.kb_retrieval.product-docs", type: "tool" as const, owner_user_id: 1, visibility: "private" as const },
  spec: {
    name: knowledgeBaseRetrievalTemplate.name,
    description: knowledgeBaseRetrievalTemplate.description,
    execution_backend: "knowledge_base_retrieval" as const,
    execution_config: knowledgeBaseRetrievalTemplate.execution_config,
    permissions: {},
    input_schema: knowledgeBaseRetrievalTemplate.input_schema,
    output_schema: knowledgeBaseRetrievalTemplate.output_schema,
    safety_policy: knowledgeBaseRetrievalTemplate.safety_policy,
    offline_compatible: true,
  },
};

const mcpCreationOptionsFixture = {
  tools: [
    {
      tool_id: "tool.web_search",
      metadata_defaults: {
        category: "web_search" as const,
        capabilities: ["web-search", "fresh-information", "source-discovery", "fact-checking", "public-research"],
        local: false,
        stateless: true,
        sandboxed: false,
        risk_level: "medium" as const,
        data_access: "public_web" as const,
        output_freshness: "fresh" as const,
        audit_level: "standard" as const,
      },
    },
    {
      tool_id: "tool.kb_retrieval.product-docs",
      metadata_defaults: {
        category: "knowledge_retrieval" as const,
        capabilities: ["knowledge-base", "retrieval", "semantic-search", "source-grounding"],
        local: true,
        stateless: true,
        sandboxed: false,
        risk_level: "low" as const,
        data_access: "workspace" as const,
        output_freshness: "static" as const,
        audit_level: "standard" as const,
      },
    },
  ],
};

const mcpServerFixture = {
  id: "mcp.web_search",
  entity: { id: "mcp.web_search", type: "mcp_server" as const, owner_user_id: 1, visibility: "private" as const },
  current_version: "v1",
  status: "published",
  published: true,
  published_at: "2026-01-01T00:00:00+00:00",
  spec: {
    name: "Web search MCP",
    slug: "web_search",
    description: "Expose Web search through the MCP gateway with a long agent-facing description that explains safe research behavior, citation expectations, result limits, and when the agent should avoid using web search.",
    backing_tool_id: "tool.web_search",
    exposed_tool_name: "web_search",
    input_schema: toolFixture.spec.input_schema,
    output_schema: toolFixture.spec.output_schema,
    metadata: {
      category: "web_search" as const,
      capabilities: ["web-search", "fresh-information", "source-discovery", "fact-checking", "public-research"],
      local: false,
      stateless: true,
      sandboxed: false,
      risk_level: "medium" as const,
      data_access: "public_web" as const,
      output_freshness: "fresh" as const,
      audit_level: "standard" as const,
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
    vi.mocked(catalogApi.getCatalogDefaults).mockResolvedValue({
      agent: {
        runtime_prompts: {
          retrieval_context: apiRetrievalDefault,
        },
      },
    });
    vi.mocked(catalogApi.getCatalogToolCreationOptions).mockResolvedValue(toolCreationOptionsFixture);
    vi.mocked(catalogApi.getCatalogMcpCreationOptions).mockResolvedValue(mcpCreationOptionsFixture);
    vi.mocked(catalogApi.listCatalogAgents).mockResolvedValue([platformAgentFixture, agentFixture]);
    vi.mocked(catalogApi.listCatalogTools).mockResolvedValue([toolFixture]);
    vi.mocked(catalogApi.listCatalogMcpServers).mockResolvedValue([]);
    vi.mocked(catalogApi.createCatalogMcpServer).mockResolvedValue(mcpServerFixture);
    vi.mocked(modelApi.listEnabledModels).mockResolvedValue([{ id: "safe-small", name: "Safe Small" }]);
    vi.mocked(catalogApi.createCatalogAgent).mockResolvedValue(agentFixture);
    vi.mocked(catalogApi.updateCatalogAgent).mockResolvedValue({ ...agentFixture, published: true });
    vi.mocked(catalogApi.deleteCatalogAgent).mockResolvedValue(undefined);
    vi.mocked(catalogApi.previewCatalogAgentPrompt).mockResolvedValue({
      prompt_preview: {
        messages: [
          { role: "system", label: "agent_instructions", content: "Backend agent instructions" },
          { role: "system", label: "retrieval_context", content: "Backend retrieval preview" },
        ],
        text: "Backend prompt preview",
      },
    });
    vi.mocked(catalogApi.validateCatalogAgent).mockResolvedValue({
      agent: agentFixture,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
        resolved_tools: [{ id: "tool.web_search", name: "Web search", execution_backend: "mcp_gateway_web_search", offline_compatible: false }],
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
    vi.mocked(catalogApi.validateCatalogMcpServer).mockResolvedValue({
      mcp_server: mcpServerFixture,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
        runtime_checks: {},
      },
    });
    vi.mocked(catalogApi.testCatalogTool).mockResolvedValue({
      tool: toolFixture,
      execution: {
        input: { query: "OpenAI platform runtime", top_k: 3 },
        request_metadata: {},
        status_code: 200,
        ok: true,
        result: { results: [{ title: "Example result" }] },
      },
    });
  });

  it("loads the overview dashboard with first-level navigation", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: "Agent and tool catalog" })).toBeVisible();
    const topNav = screen.getByRole("navigation", { name: "Catalog control sections" });
    expect(within(topNav).getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(within(topNav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Overview", "Tools", "MCP Gateway", "Agents"]);
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
    expect((screen.getByLabelText("Retrieval instructions") as HTMLTextAreaElement).value).toBe(apiRetrievalDefault);
    await waitFor(() => {
      expect(catalogApi.previewCatalogAgentPrompt).toHaveBeenCalledWith(
        expect.objectContaining({
          instructions: expect.stringContaining("Use tools carefully."),
        }),
        "token",
      );
    });
    expect((screen.getByLabelText("Prompt review") as HTMLTextAreaElement).value).toBe("Backend prompt preview");
    await user.click(screen.getByRole("button", { name: "Create agent" }));

    await waitFor(() => {
      expect(catalogApi.createCatalogAgent).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "agent.beta",
          name: "Agent Beta",
          publish: false,
          runtime_prompts: expect.objectContaining({
            retrieval_context: apiRetrievalDefault,
          }),
        }),
        "token",
      );
    });
  });

  it("splits platform agents from user agents", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=agents&view=agents" });

    const subNav = await screen.findByRole("navigation", { name: "Agent catalog sections" });
    const userAgentsLink = within(subNav).getByRole("link", { name: "User agents" });
    expect(within(subNav).getByRole("link", { name: "Platform agents" })).toHaveAttribute("aria-current", "page");
    expect(userAgentsLink).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Knowledge Chat" })).toBeVisible();
    expectCompactRegistryRowForHeading("Knowledge Chat");
    expect(screen.queryByRole("heading", { name: "Agent Alpha" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Knowledge Chat" })).not.toBeInTheDocument();
    expectNamedIconAction("button", "Edit Knowledge Chat");
    expectNamedIconAction("button", "Validate Knowledge Chat");
    expectNoGenericCompactActions(["Edit", "Validate", "Delete"]);

    await user.click(userAgentsLink);

    expect(await screen.findByRole("heading", { name: "Agent Alpha" })).toBeVisible();
    expectCompactRegistryRowForHeading("Agent Alpha");
    expect(screen.queryByRole("heading", { name: "Knowledge Chat" })).not.toBeInTheDocument();
    expectNamedIconAction("button", "Delete Agent Alpha");
  });

  it("deletes a user agent after confirmation", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=agents&view=user-agents" });

    await user.click(await screen.findByRole("button", { name: "Delete Agent Alpha" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete user agent" });
    expect(within(dialog).getByText("Delete Agent Alpha? This removes the catalog agent and its versions.")).toBeVisible();

    await user.click(within(dialog).getByRole("button", { name: "Delete agent" }));

    await waitFor(() => {
      expect(catalogApi.deleteCatalogAgent).toHaveBeenCalledWith("agent.alpha", "token");
    });
  });

  it("validates a tool and renders validation errors", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=tools" });

    const subNav = await screen.findByRole("navigation", { name: "Tool catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Platform tools" })).toHaveAttribute("aria-current", "page");

    await user.click(await screen.findByRole("button", { name: "Validate Web search" }));

    await waitFor(() => {
      expect(catalogApi.validateCatalogTool).toHaveBeenCalledWith("tool.web_search", "token");
    });
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("MCP gateway does not expose tool 'web_search'.")).toBeVisible();
  });

  it("creates a tool from backend-owned execution templates", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=create" });

    expect(await screen.findByRole("heading", { name: "Create tool" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Create tool" })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Execution backend"), "mcp_gateway_web_search");

    expect(screen.getByLabelText("Tool ID")).toHaveValue("tool.custom_web_search");
    expect(screen.getByLabelText("Name")).toHaveValue("Web Search");
    expect(screen.getByLabelText("Input schema")).toHaveValue(JSON.stringify(toolFixture.spec.input_schema, null, 2));
    expect(screen.getByRole("button", { name: "Create tool" })).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Create tool" }));

    await waitFor(() => {
      expect(catalogApi.createCatalogTool).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "tool.custom_web_search",
          execution_backend: "mcp_gateway_web_search",
          name: "Web Search",
        }),
        "token",
      );
    });
  });

  it("creates a knowledge-base retrieval tool for a bound knowledge base", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=create" });

    expect(await screen.findByRole("heading", { name: "Create tool" })).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Execution backend"), "knowledge_base_retrieval");

    expect(screen.getByLabelText("Knowledge base")).toHaveValue("kb-product-docs");
    expect(screen.getByLabelText("Tool ID")).toHaveValue("tool.kb_retrieval.product-docs");
    expect(screen.getByLabelText("Name")).toHaveValue("Product Docs Retrieval");
    expect(screen.getByLabelText("Execution config")).toHaveValue(JSON.stringify(knowledgeBaseRetrievalTemplate.execution_config, null, 2));

    await user.click(screen.getByRole("button", { name: "Create tool" }));

    await waitFor(() => {
      expect(catalogApi.createCatalogTool).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "tool.kb_retrieval.product-docs",
          execution_backend: "knowledge_base_retrieval",
          execution_config: expect.objectContaining({
            knowledge_base_id: "kb-product-docs",
          }),
          offline_compatible: true,
        }),
        "token",
      );
    });
  });

  it("opens the edit flow from the tools directory", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=tools" });

    await user.click(await screen.findByRole("button", { name: "Edit Web search" }));

    expect(await screen.findByRole("heading", { name: "Create tool" })).toBeVisible();
    expect(screen.getByLabelText("Tool ID")).toHaveValue("tool.web_search");
    const subNav = screen.getByRole("navigation", { name: "Tool catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Create tool" })).toHaveAttribute("aria-current", "page");
  });

  it("opens the test flow from the tools directory and runs the tool with sample input", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=tools&view=tools" });

    await user.click(await screen.findByRole("button", { name: "Test Web search" }));

    expect(await screen.findByRole("heading", { name: "Test tool" })).toBeVisible();
    const subNav = screen.getByRole("navigation", { name: "Tool catalog sections" });
    expect(within(subNav).getByRole("link", { name: "Web search" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("Test input")).toHaveValue('{\n  "query": "OpenAI platform runtime",\n  "top_k": 3\n}');

    await user.click(screen.getByRole("button", { name: "Test" }));

    await waitFor(() => {
      expect(catalogApi.testCatalogTool).toHaveBeenCalledWith(
        "tool.web_search",
        { query: "OpenAI platform runtime", top_k: 3 },
        "token",
      );
    });
    const resultPanel = await screen.findByTestId("catalog-tool-test-result");
    expect(resultPanel).toBeVisible();
    expect(resultPanel).toHaveTextContent("Example result");
  });

  it("starts MCP server creation from the backing tool and fills defaults", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=create" });

    expect(await screen.findByRole("heading", { name: "Create MCP server" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Create MCP server" })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("Backing internal tool"), "tool.web_search");

    expect(screen.getByLabelText("MCP server ID")).toHaveValue("mcp.web_search");
    expect(screen.getByLabelText("Name")).toHaveValue("Web search MCP");
    expect(screen.getByLabelText("Slug")).toHaveValue("web_search");
    expect(screen.getByLabelText("Exposed MCP tool name")).toHaveValue("web_search");
    expect(screen.getByLabelText("Description for agents")).toHaveValue("Expose Web search through the MCP gateway.");
    expect(screen.getByLabelText("Category")).toHaveValue("web_search");
    expect(screen.getByLabelText("Capabilities")).toHaveValue("web-search, fresh-information, source-discovery, fact-checking, public-research");
    expect(screen.getByLabelText("Input schema")).toHaveValue(JSON.stringify(toolFixture.spec.input_schema, null, 2));

    await user.click(screen.getByRole("button", { name: "Create MCP server" }));

    await waitFor(() => {
      expect(catalogApi.createCatalogMcpServer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "mcp.web_search",
          backing_tool_id: "tool.web_search",
          slug: "web_search",
          exposed_tool_name: "web_search",
          name: "Web search MCP",
          metadata: expect.objectContaining({
            category: "web_search",
            risk_level: "medium",
            local: false,
          }),
        }),
        "token",
      );
    });
  });

  it("fills MCP metadata defaults for knowledge-base retrieval tools", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogTools).mockResolvedValue([toolFixture, kbRetrievalToolFixture]);

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=create" });

    expect(await screen.findByRole("heading", { name: "Create MCP server" })).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Backing internal tool"), "tool.kb_retrieval.product-docs");

    expect(screen.getByLabelText("MCP server ID")).toHaveValue("mcp.kb_retrieval.product-docs");
    expect(screen.getByLabelText("Category")).toHaveValue("knowledge_retrieval");
    expect(screen.getByLabelText("Capabilities")).toHaveValue("knowledge-base, retrieval, semantic-search, source-grounding");
    expect(screen.getByLabelText("Local")).toHaveValue("true");
    expect(screen.getByLabelText("Risk level")).toHaveValue("low");
    expect(screen.getByLabelText("Data access")).toHaveValue("workspace");
    expect(screen.getByLabelText("Output freshness")).toHaveValue("static");
  });

  it("opens a dedicated MCP edit flow with the backing tool locked", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogMcpServers).mockResolvedValue([mcpServerFixture]);
    vi.mocked(catalogApi.updateCatalogMcpServer).mockResolvedValue({
      ...mcpServerFixture,
      spec: {
        ...mcpServerFixture.spec,
        name: "Web search MCP updated",
      },
    });

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=registry" });

    await user.click(await screen.findByRole("button", { name: "Edit Web search MCP" }));

    expect(await screen.findByRole("heading", { name: "Edit Web search MCP" })).toBeVisible();
    const subNav = screen.getByRole("navigation", { name: "MCP Gateway sections" });
    expect(within(subNav).getByRole("link", { name: "Edit Web search MCP" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("Backing internal tool")).toBeDisabled();
    expect(screen.getByLabelText("Backing internal tool")).toHaveValue("tool.web_search");

    await user.clear(screen.getByLabelText("Name"));
    await user.type(screen.getByLabelText("Name"), "Web search MCP updated");
    await user.click(screen.getByRole("button", { name: "Update MCP server" }));

    await waitFor(() => {
      expect(catalogApi.updateCatalogMcpServer).toHaveBeenCalledWith(
        "mcp.web_search",
        expect.objectContaining({
          name: "Web search MCP updated",
          backing_tool_id: "tool.web_search",
        }),
        "token",
      );
    });
  });

  it("resets the MCP form when moving from edit back to create", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogMcpServers).mockResolvedValue([mcpServerFixture]);

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=registry" });

    await user.click(await screen.findByRole("button", { name: "Edit Web search MCP" }));
    expect(await screen.findByRole("heading", { name: "Edit Web search MCP" })).toBeVisible();
    expect(screen.getByLabelText("Backing internal tool")).toBeDisabled();

    const subNav = screen.getByRole("navigation", { name: "MCP Gateway sections" });
    await user.click(within(subNav).getByRole("link", { name: "Create MCP server" }));

    expect(await screen.findByRole("heading", { name: "Create MCP server" })).toBeVisible();
    expect(screen.getByLabelText("Backing internal tool")).not.toBeDisabled();
    expect(screen.getByLabelText("Backing internal tool")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Create MCP server" })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("Backing internal tool"), "tool.web_search");

    expect(screen.getByLabelText("MCP server ID")).toHaveValue("mcp.web_search_2");
    expect(screen.getByRole("button", { name: "Create MCP server" })).not.toBeDisabled();
  });

  it("renders a compact MCP registry and opens full descriptions in a modal", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.listCatalogMcpServers).mockResolvedValue([mcpServerFixture]);

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=registry" });

    expect(await screen.findByRole("heading", { name: "Web search MCP" })).toBeVisible();
    expectCompactRegistryRowForHeading("Web search MCP");
    expect(screen.getByText("Enabled")).toBeVisible();
    expect(screen.getByText("Validated")).toBeVisible();
    expect(screen.getByText("Expose Web search through the MCP gateway with a long agent-facing description that explains safe research...")).toBeVisible();
    expect(screen.queryByText(mcpServerFixture.spec.description)).not.toBeInTheDocument();
    expectNamedIconAction("button", "Edit Web search MCP");
    expectNamedIconAction("button", "Disable Web search MCP");
    expectNamedIconAction("button", "Validate Web search MCP");
    expectNamedIconAction("button", "Delete Web search MCP");
    expectNoGenericCompactActions(["Edit", "Disable", "Validate", "Delete"]);

    await user.click(screen.getByRole("button", { name: "View full description for Web search MCP" }));

    const dialog = await screen.findByRole("dialog", { name: "Web search MCP description" });
    expect(within(dialog).getByText(mcpServerFixture.spec.description)).toBeVisible();
  });

  it("updates the MCP validation badge after validation runs", async () => {
    const user = userEvent.setup();
    const unvalidatedServer = {
      ...mcpServerFixture,
      validation_status: {
        ...mcpServerFixture.validation_status,
        last_validation_status: "unknown",
        is_validation_current: false,
        validated_version: null,
      },
    };
    vi.mocked(catalogApi.listCatalogMcpServers).mockResolvedValue([unvalidatedServer]);

    await renderWithAppProviders(<CatalogControlPage />, { route: "/control/catalog?section=mcp&view=registry" });

    expect(await screen.findByText("Needs validation")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Validate Web search MCP" }));

    await waitFor(() => {
      expect(catalogApi.validateCatalogMcpServer).toHaveBeenCalledWith("mcp.web_search", "token");
    });
    expect(await screen.findByText("Validated")).toBeVisible();
  });
});
