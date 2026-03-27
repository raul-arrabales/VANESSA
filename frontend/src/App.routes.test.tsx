import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import App from "./App";
import { renderWithAppProviders } from "./test/renderWithAppProviders";
import { t } from "./test/translation";

let mockUser: AuthUser | null = null;

vi.mock("./auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
    activatePendingUser: vi.fn(),
    listPendingUsers: vi.fn(),
    updateUserRole: vi.fn(),
  }),
}));


vi.mock("./runtime/RuntimeModeProvider", () => ({
  useRuntimeMode: () => ({
    mode: "offline",
    isLocked: false,
    source: "database",
    isLoading: false,
    isSaving: false,
    error: "",
    setMode: vi.fn(),
  }),
}));
vi.mock("./api/modelops", () => ({
  listModelOpsModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4", lifecycle_state: "active", is_validation_current: true, last_validation_status: "success" }]),
  listModelAssignments: vi.fn(async () => [{ scope: "superadmin", model_ids: ["gpt-4"] }]),
  listDownloadJobs: vi.fn(async () => []),
  listLocalModelArtifacts: vi.fn(async () => []),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  listEnabledModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  runInference: vi.fn(),
  listModelCredentials: vi.fn(async () => []),
  getManagedModel: vi.fn(async () => ({ id: "gpt-4", name: "GPT-4", provider: "openai_compatible", backend: "external_api", lifecycle_state: "active", is_validation_current: true, last_validation_status: "success", task_key: "llm", visibility_scope: "platform", owner_type: "platform", usage_summary: { total_requests: 5, metrics: {} }, artifact: {} })),
  getManagedModelUsage: vi.fn(async () => ({ model_id: "gpt-4", usage: { total_requests: 5, metrics: {} } })),
  getManagedModelValidations: vi.fn(async () => ({ model_id: "gpt-4", validations: [] })),
  listManagedModelTests: vi.fn(async () => ({ model_id: "gpt-4", tests: [] })),
  runManagedModelTest: vi.fn(),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
  registerExistingManagedModel: vi.fn(),
  validateManagedModel: vi.fn(),
  activateManagedModel: vi.fn(),
  deactivateManagedModel: vi.fn(),
  unregisterManagedModel: vi.fn(),
  deleteManagedModel: vi.fn(),
  discoverHfModels: vi.fn(async () => []),
  getHfModelDetails: vi.fn(async () => ({ source_id: "hf/model", name: "model", files: [] })),
  startModelDownload: vi.fn(),
}));
vi.mock("./api/modelops/models", () => ({
  listEnabledModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  registerManagedModel: vi.fn(),
  listAvailableManagedModels: vi.fn(),
  listModelOpsModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4", lifecycle_state: "active", is_validation_current: true, last_validation_status: "success" }]),
  getManagedModel: vi.fn(async () => ({
    id: "gpt-4",
    name: "GPT-4",
    provider: "openai_compatible",
    backend: "external_api",
    lifecycle_state: "active",
    is_validation_current: true,
    last_validation_status: "success",
    task_key: "llm",
    visibility_scope: "platform",
    owner_type: "platform",
    usage_summary: { total_requests: 5, metrics: {} },
    artifact: {},
  })),
  getManagedModelUsage: vi.fn(async () => ({ model_id: "gpt-4", usage: { total_requests: 5, metrics: {} } })),
  getManagedModelValidations: vi.fn(async () => ({ model_id: "gpt-4", validations: [] })),
  registerExistingManagedModel: vi.fn(),
  activateManagedModel: vi.fn(),
  deactivateManagedModel: vi.fn(),
  unregisterManagedModel: vi.fn(),
  deleteManagedModel: vi.fn(),
}));
vi.mock("./api/modelops/testing", () => ({
  listManagedModelTests: vi.fn(async () => ({ model_id: "gpt-4", tests: [] })),
  runManagedModelTest: vi.fn(),
  validateManagedModel: vi.fn(),
}));
vi.mock("./api/modelops/credentials", () => ({
  listModelCredentials: vi.fn(async () => []),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
}));
vi.mock("./api/modelops/local", () => ({
  listDownloadJobs: vi.fn(async () => []),
  listLocalModelArtifacts: vi.fn(async () => []),
  createModelCatalogItem: vi.fn(),
  discoverHfModels: vi.fn(async () => []),
  getHfModelDetails: vi.fn(async () => ({ source_id: "hf/model", name: "model", files: [] })),
  startModelDownload: vi.fn(),
}));
vi.mock("./api/modelops/access", () => ({
  listModelAssignments: vi.fn(async () => [{ scope: "superadmin", model_ids: ["gpt-4"] }]),
  updateModelAssignment: vi.fn(),
}));
vi.mock("./api/playgrounds", () => ({
  getPlaygroundOptions: vi.fn(async () => ({
    assistants: [],
    models: [{ id: "gpt-4", display_name: "GPT-4" }],
    knowledge_bases: [{ id: "kb-primary", display_name: "Product Docs", index_name: "kb_product_docs", is_default: true }],
    default_knowledge_base_id: "kb-primary",
    selection_required: false,
    configuration_message: null,
  })),
  listPlaygroundSessions: vi.fn(async (kind: string) => (
    kind === "knowledge"
      ? [{ id: "sess-1", playground_kind: "knowledge", assistant_ref: "agent.knowledge_chat", title: "Knowledge session", title_source: "auto", model_selection: { model_id: "gpt-4" }, knowledge_binding: { knowledge_base_id: "kb-primary" }, message_count: 0, created_at: "2026-03-18T11:00:00Z", updated_at: "2026-03-18T11:00:00Z" }]
      : [{ id: "sess-chat", playground_kind: "chat", assistant_ref: "assistant.playground.chat", title: "Chat session", title_source: "auto", model_selection: { model_id: "gpt-4" }, knowledge_binding: { knowledge_base_id: null }, message_count: 0, created_at: "2026-03-18T11:00:00Z", updated_at: "2026-03-18T11:00:00Z" }]
  )),
  createPlaygroundSession: vi.fn(async (payload: { playground_kind: string }) => ({
    id: payload.playground_kind === "knowledge" ? "sess-1" : "sess-chat",
    playground_kind: payload.playground_kind,
    assistant_ref: payload.playground_kind === "knowledge" ? "agent.knowledge_chat" : "assistant.playground.chat",
    title: payload.playground_kind === "knowledge" ? "Knowledge session" : "Chat session",
    title_source: "auto",
    model_selection: { model_id: "gpt-4" },
    knowledge_binding: { knowledge_base_id: payload.playground_kind === "knowledge" ? "kb-primary" : null },
    message_count: 0,
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
    messages: [],
  })),
  getPlaygroundSession: vi.fn(async (_sessionId: string, kind: string) => ({
    id: kind === "knowledge" ? "sess-1" : "sess-chat",
    playground_kind: kind,
    assistant_ref: kind === "knowledge" ? "agent.knowledge_chat" : "assistant.playground.chat",
    title: kind === "knowledge" ? "Knowledge session" : "Chat session",
    title_source: "auto",
    model_selection: { model_id: "gpt-4" },
    knowledge_binding: { knowledge_base_id: kind === "knowledge" ? "kb-primary" : null },
    message_count: 0,
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
    messages: [],
  })),
  updatePlaygroundSession: vi.fn(),
  deletePlaygroundSession: vi.fn(),
  sendPlaygroundMessage: vi.fn(),
  streamPlaygroundMessage: vi.fn(),
}));
vi.mock("./api/catalog", () => ({
  listCatalogAgents: vi.fn(async () => []),
  createCatalogAgent: vi.fn(),
  updateCatalogAgent: vi.fn(),
  validateCatalogAgent: vi.fn(),
  listCatalogTools: vi.fn(async () => []),
  createCatalogTool: vi.fn(),
  updateCatalogTool: vi.fn(),
  validateCatalogTool: vi.fn(),
}));
vi.mock("./api/agentProjects", () => ({
  listAgentProjects: vi.fn(async () => [{
    id: "proj-1",
    owner_user_id: 1,
    published_agent_id: null,
    current_version: 1,
    visibility: "private",
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
    spec: {
      name: "Support Agent",
      description: "Handles support workflows.",
      instructions: "Be helpful.",
      default_model_ref: "gpt-4",
      tool_refs: ["tool.web_search"],
      workflow_definition: { entrypoint: "assistant" },
      tool_policy: { allow_user_tools: false },
      runtime_constraints: { internet_required: true, sandbox_required: false },
    },
  }]),
  createAgentProject: vi.fn(),
  getAgentProject: vi.fn(async () => ({
    id: "proj-1",
    owner_user_id: 1,
    published_agent_id: null,
    current_version: 1,
    visibility: "private",
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
    spec: {
      name: "Support Agent",
      description: "Handles support workflows.",
      instructions: "Be helpful.",
      default_model_ref: "gpt-4",
      tool_refs: ["tool.web_search"],
      workflow_definition: { entrypoint: "assistant" },
      tool_policy: { allow_user_tools: false },
      runtime_constraints: { internet_required: true, sandbox_required: false },
    },
  })),
  updateAgentProject: vi.fn(),
  validateAgentProject: vi.fn(),
  publishAgentProject: vi.fn(),
}));
vi.mock("./api/platform", () => ({
  listPlatformCapabilities: vi.fn(async () => [
    {
      capability: "llm_inference",
      display_name: "LLM inference",
      description: "desc",
      required: true,
      active_provider: {
        id: "provider-1",
        slug: "vllm-local-gateway",
        provider_key: "vllm_local",
        display_name: "vLLM local gateway",
        deployment_profile_id: "deployment-1",
        deployment_profile_slug: "local-default",
      },
    },
  ]),
  listPlatformProviderFamilies: vi.fn(async () => [
    {
      provider_key: "vllm_local",
      capability: "llm_inference",
      adapter_kind: "openai_compatible_llm",
      display_name: "vLLM local gateway",
      description: "desc",
    },
  ]),
  listPlatformProviders: vi.fn(async () => [
    {
      id: "provider-1",
      slug: "vllm-local-gateway",
      provider_key: "vllm_local",
      capability: "llm_inference",
      adapter_kind: "openai_compatible_llm",
      display_name: "vLLM local gateway",
      description: "desc",
      endpoint_url: "http://llm:8000",
      healthcheck_url: "http://llm:8000/health",
      enabled: true,
      config: {},
      secret_refs: {},
    },
  ]),
  listPlatformDeployments: vi.fn(async () => [
    {
      id: "deployment-1",
      slug: "local-default",
      display_name: "Local Default",
      description: "desc",
      is_active: true,
      bindings: [],
    },
  ]),
  listPlatformActivationAudit: vi.fn(async () => []),
  validatePlatformProvider: vi.fn(),
  createPlatformProvider: vi.fn(),
  updatePlatformProvider: vi.fn(),
  deletePlatformProvider: vi.fn(),
  createDeploymentProfile: vi.fn(),
  updateDeploymentProfile: vi.fn(),
  cloneDeploymentProfile: vi.fn(),
  deleteDeploymentProfile: vi.fn(),
  activateDeploymentProfile: vi.fn(),
}));
vi.mock("./api/quoteAdmin", () => ({
  fetchQuoteSummary: vi.fn(async () => ({
    total: 2,
    active: 2,
    approved: 2,
    by_language: [],
    by_tone: [],
    by_origin: [],
  })),
  fetchQuotes: vi.fn(async () => ({
    items: [],
    page: 1,
    page_size: 10,
    total: 0,
    filters: {},
  })),
  fetchQuoteById: vi.fn(),
  createQuote: vi.fn(),
  updateQuote: vi.fn(),
}));

describe("App superadmin models route", () => {
  it("renders the page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    expect(await screen.findByRole("heading", { name: await t("modelOps.home.title") })).toBeVisible();
  });

  it("renders the model test page for admin", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models/gpt-4/test" });

    expect(await screen.findByRole("heading", { name: "GPT-4" })).toBeVisible();
  });

  it("navigates the main modelops flow from home to catalog, detail, and test", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    expect(await screen.findByRole("heading", { name: await t("modelOps.home.title") })).toBeVisible();

    await userEvent.click(screen.getByRole("link", { name: "Browse catalog" }));
    expect(await screen.findByRole("heading", { name: await t("modelOps.catalog.title") })).toBeVisible();

    await userEvent.click(screen.getByRole("link", { name: "Open details" }));
    expect(await screen.findByRole("heading", { name: "GPT-4" })).toBeVisible();

    await userEvent.click(screen.getByRole("link", { name: "Test model" }));
    expect(await screen.findByLabelText("Prompt")).toBeVisible();
    expect(screen.getByRole("button", { name: "Mark as validated" })).toBeDisabled();
  });

  it("blocks non-superadmin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/system-health" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("renders the platform control page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/platform" });

    expect(await screen.findByRole("heading", { name: await t("platformControl.title") })).toBeVisible();
  });

  it("renders the catalog control page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/catalog" });

    expect(await screen.findByRole("heading", { name: await t("catalogControl.title") })).toBeVisible();
  });

  it("renders the agent builder page for users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/agent-builder" });

    expect(await screen.findByRole("heading", { name: await t("agentBuilder.title") })).toBeVisible();
  });

  it("blocks admin users from the platform control route", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/platform" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("blocks admin users from the catalog control route", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/catalog" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("renders the quote management page for admin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/quotes" });

    expect(await screen.findByRole("heading", { name: await t("quoteAdmin.title") })).toBeVisible();
  });

  it("blocks regular users from the quote management route", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/quotes" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("falls through removed legacy routes to not-found", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/chat" });

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeVisible();
  });

  it("renders the knowledge chat page for authenticated users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/ai/knowledge" });

    expect(await screen.findByRole("heading", { name: "Knowledge playground" })).toBeVisible();
  });

  it("always shows Home as the first breadcrumb link", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    const breadcrumbLinks = await screen.findAllByRole("link", { name: await t("nav.home") });
    expect(breadcrumbLinks[0]).toHaveAttribute("href", "/");
  });

  it("renders the control breadcrumb with the control panel label", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    expect(await screen.findByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute("href", "/control");
  });

  it("renders the model catalog subroute for authenticated users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models/catalog" });

    expect(await screen.findByRole("heading", { name: await t("modelOps.catalog.title") })).toBeVisible();
  });

  it("renders the access management route for admin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models/access" });

    expect(await screen.findByRole("heading", { name: await t("modelOps.access.title") })).toBeVisible();
  });

  it("blocks regular users from the local registration route", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models/local/register" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });
});
