import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createCatalogAgent,
  createCatalogMcpServer,
  createCatalogTool,
  deleteCatalogAgent,
  deleteCatalogMcpServer,
  getCatalogDefaults,
  getCatalogMcpCreationOptions,
  getCatalogToolCreationOptions,
  listCatalogAgents,
  listCatalogMcpServers,
  listCatalogTools,
  previewCatalogAgentPrompt,
  type CatalogAgent,
  type CatalogAgentMutationInput,
  type CatalogAgentValidation,
  type CatalogDefaults,
  type CatalogMcpServer,
  type CatalogMcpCreationOptions,
  type CatalogMcpServerMutationInput,
  type CatalogMcpServerSpec,
  type CatalogMcpServerValidation,
  type CatalogTool,
  type CatalogToolCreationOptions,
  type CatalogToolExecutionBackend,
  type CatalogToolMutationInput,
  type CatalogToolValidation,
  setCatalogMcpServerEnabled,
  updateCatalogAgent,
  updateCatalogMcpServer,
  updateCatalogTool,
  validateCatalogAgent,
  validateCatalogMcpServer,
  validateCatalogTool,
} from "../../../api/catalog";
import { listEnabledModels, type ModelCatalogItem } from "../../../api/modelops";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { useCatalogToolTesting } from "./useCatalogToolTesting";

export type CatalogLoadState = "idle" | "loading" | "success" | "error";
type FormMode = "create" | "edit";

export type AgentFormState = CatalogAgentMutationInput & {
  mode: FormMode;
  agentId: string;
};

export type ToolFormState = Omit<CatalogToolMutationInput, "execution_backend"> & {
  execution_backend: CatalogToolExecutionBackend | "";
  mode: FormMode;
  toolId: string;
  selectedKnowledgeBaseId: string;
  inputSchemaText: string;
  outputSchemaText: string;
  safetyPolicyText: string;
  executionConfigText: string;
  permissionsText: string;
};

export type McpServerFormState = CatalogMcpServerMutationInput & {
  mode: FormMode;
  mcpServerId: string;
  inputSchemaText: string;
  outputSchemaText: string;
  capabilitiesText: string;
  agentIdsText: string;
  agentDomainsText: string;
  agentRolesText: string;
  userRolesText: string;
  userIdsText: string;
  userGroupIdsText: string;
};

function agentRuntimePromptsFromDefaults(defaults: CatalogDefaults | null): CatalogAgentMutationInput["runtime_prompts"] {
  return {
    retrieval_context: defaults?.agent.runtime_prompts.retrieval_context ?? "",
  };
}

export function buildDefaultAgentForm(defaults: CatalogDefaults | null): AgentFormState {
  return {
    mode: "create",
    agentId: "",
    id: "",
    visibility: "private",
    publish: false,
    name: "",
    description: "",
    instructions: "",
    runtime_prompts: agentRuntimePromptsFromDefaults(defaults),
    default_model_ref: null,
    tool_refs: [],
    mcp_server_refs: [],
    agent_domain: "default",
    runtime_constraints: {
      internet_required: false,
      sandbox_required: false,
    },
  };
}

export const DEFAULT_AGENT_FORM: AgentFormState = buildDefaultAgentForm(null);

export const DEFAULT_TOOL_FORM: ToolFormState = {
  mode: "create",
  toolId: "",
  id: "",
  visibility: "private",
  publish: false,
  name: "",
  description: "",
  input_schema: {},
  output_schema: {},
  safety_policy: {},
  offline_compatible: false,
  execution_backend: "",
  execution_config: {},
  permissions: {},
  selectedKnowledgeBaseId: "",
  inputSchemaText: "{}",
  outputSchemaText: "{}",
  safetyPolicyText: "{}",
  executionConfigText: "{}",
  permissionsText: "{}",
};

export const DEFAULT_MCP_SERVER_FORM: McpServerFormState = {
  mode: "create",
  mcpServerId: "",
  id: "",
  visibility: "private",
  publish: true,
  name: "",
  slug: "",
  description: "",
  backing_tool_id: "",
  exposed_tool_name: "",
  input_schema: {},
  output_schema: {},
  metadata: {
    category: "custom",
    capabilities: [],
    local: false,
    stateless: true,
    sandboxed: false,
    risk_level: "medium",
    data_access: "none",
    output_freshness: "runtime_generated",
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
  inputSchemaText: "{}",
  outputSchemaText: "{}",
  capabilitiesText: "",
  agentIdsText: "*",
  agentDomainsText: "*",
  agentRolesText: "*",
  userRolesText: "*",
  userIdsText: "*",
  userGroupIdsText: "*",
};

function stringifyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

export function buildAgentForm(agent: CatalogAgent): AgentFormState {
  return {
    mode: "edit",
    agentId: agent.id,
    id: agent.id,
    visibility: agent.entity.visibility,
    publish: agent.published,
    name: agent.spec.name,
    description: agent.spec.description,
    instructions: agent.spec.instructions,
    runtime_prompts: {
      retrieval_context: agent.spec.runtime_prompts?.retrieval_context ?? "",
    },
    default_model_ref: agent.spec.default_model_ref,
    tool_refs: agent.spec.tool_refs,
    mcp_server_refs: agent.spec.mcp_server_refs ?? [],
    agent_domain: agent.spec.agent_domain ?? "default",
    runtime_constraints: {
      internet_required: agent.spec.runtime_constraints.internet_required,
      sandbox_required: agent.spec.runtime_constraints.sandbox_required,
    },
  };
}

export function buildToolForm(tool: CatalogTool): ToolFormState {
  return {
    mode: "edit",
    toolId: tool.id,
    id: tool.id,
    visibility: tool.entity.visibility,
    publish: tool.published,
    name: tool.spec.name,
    description: tool.spec.description,
    input_schema: tool.spec.input_schema,
    output_schema: tool.spec.output_schema,
    safety_policy: tool.spec.safety_policy,
    offline_compatible: tool.spec.offline_compatible,
    execution_backend: tool.spec.execution_backend ?? "internal_http",
    execution_config: tool.spec.execution_config ?? {},
    permissions: tool.spec.permissions ?? {},
    selectedKnowledgeBaseId: String((tool.spec.execution_config ?? {}).knowledge_base_id ?? ""),
    inputSchemaText: stringifyJson(tool.spec.input_schema),
    outputSchemaText: stringifyJson(tool.spec.output_schema),
    safetyPolicyText: stringifyJson(tool.spec.safety_policy),
    executionConfigText: stringifyJson(tool.spec.execution_config ?? {}),
    permissionsText: stringifyJson(tool.spec.permissions ?? {}),
  };
}

function textToList(text: string): string[] {
  const items = text.split(",").map((item) => item.trim()).filter(Boolean);
  return items.length > 0 ? items : ["*"];
}

function textToTags(text: string): string[] {
  return text.split(",").map((item) => item.trim()).filter(Boolean);
}

function listToText(items: string[]): string {
  return items.join(", ");
}

export function buildMcpServerForm(server: CatalogMcpServer): McpServerFormState {
  const policy = server.spec.authorization_policy;
  const metadata: CatalogMcpServerSpec["metadata"] = {
    ...DEFAULT_MCP_SERVER_FORM.metadata,
    ...server.spec.metadata,
  };
  return {
    mode: "edit",
    mcpServerId: server.id,
    id: server.id,
    visibility: server.entity.visibility,
    publish: server.published,
    name: server.spec.name,
    slug: server.spec.slug,
    description: server.spec.description,
    backing_tool_id: server.spec.backing_tool_id,
    exposed_tool_name: server.spec.exposed_tool_name,
    input_schema: server.spec.input_schema,
    output_schema: server.spec.output_schema,
    metadata,
    authorization_policy: policy,
    enabled: server.spec.enabled,
    inputSchemaText: stringifyJson(server.spec.input_schema),
    outputSchemaText: stringifyJson(server.spec.output_schema),
    capabilitiesText: listToText(metadata.capabilities),
    agentIdsText: listToText(policy.agent_ids),
    agentDomainsText: listToText(policy.agent_domains),
    agentRolesText: listToText(policy.agent_roles),
    userRolesText: listToText(policy.user_roles),
    userIdsText: listToText(policy.user_ids),
    userGroupIdsText: listToText(policy.user_group_ids),
  };
}

export function useCatalogControl(token: string) {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [state, setState] = useState<CatalogLoadState>("idle");
  const [agents, setAgents] = useState<CatalogAgent[]>([]);
  const [tools, setTools] = useState<CatalogTool[]>([]);
  const [mcpServers, setMcpServers] = useState<CatalogMcpServer[]>([]);
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [toolCreationOptions, setToolCreationOptions] = useState<CatalogToolCreationOptions | null>(null);
  const [mcpCreationOptions, setMcpCreationOptions] = useState<CatalogMcpCreationOptions | null>(null);
  const [agentForm, setAgentForm] = useState<AgentFormState>(() => buildDefaultAgentForm(null));
  const [toolForm, setToolForm] = useState<ToolFormState>(DEFAULT_TOOL_FORM);
  const [mcpServerForm, setMcpServerForm] = useState<McpServerFormState>(DEFAULT_MCP_SERVER_FORM);
  const [agentValidationResults, setAgentValidationResults] = useState<Record<string, CatalogAgentValidation>>({});
  const [toolValidationResults, setToolValidationResults] = useState<Record<string, CatalogToolValidation>>({});
  const [mcpValidationResults, setMcpValidationResults] = useState<Record<string, CatalogMcpServerValidation>>({});
  const [validatingAgentId, setValidatingAgentId] = useState("");
  const [validatingToolId, setValidatingToolId] = useState("");
  const [validatingMcpServerId, setValidatingMcpServerId] = useState("");
  const [deletingAgentId, setDeletingAgentId] = useState("");
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingTool, setSavingTool] = useState(false);
  const [savingMcpServer, setSavingMcpServer] = useState(false);
  const [agentPromptPreview, setAgentPromptPreview] = useState("");
  const [agentPromptPreviewLoading, setAgentPromptPreviewLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const catalogDefaultsRef = useRef<CatalogDefaults | null>(null);
  const promptPreviewRequestId = useRef(0);
  const toolTesting = useCatalogToolTesting(token);

  const loadCatalogState = useCallback(async (): Promise<void> => {
    if (!token) {
      setState("idle");
      setErrorMessage("");
      setAgents([]);
      setTools([]);
      setMcpServers([]);
      setModels([]);
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [
        defaultsPayload,
        agentsPayload,
        toolsPayload,
        mcpServersPayload,
        modelsPayload,
        toolCreationOptionsPayload,
        mcpCreationOptionsPayload,
      ] = await Promise.all([
        getCatalogDefaults(token),
        listCatalogAgents(token),
        listCatalogTools(token),
        listCatalogMcpServers(token),
        listEnabledModels(token),
        getCatalogToolCreationOptions(token),
        getCatalogMcpCreationOptions(token),
      ]);
      const previousDefaults = catalogDefaultsRef.current;
      catalogDefaultsRef.current = defaultsPayload;
      setAgents(agentsPayload);
      setTools(toolsPayload);
      setMcpServers(mcpServersPayload);
      setModels(modelsPayload);
      setToolCreationOptions(toolCreationOptionsPayload);
      setMcpCreationOptions(mcpCreationOptionsPayload);
      setAgentForm((current) => {
        if (current.mode !== "create") {
          return current;
        }
        const currentRetrievalContext = (current.runtime_prompts.retrieval_context ?? "").trim();
        const previousRetrievalDefault = previousDefaults?.agent.runtime_prompts.retrieval_context.trim() ?? "";
        if (currentRetrievalContext && currentRetrievalContext !== previousRetrievalDefault) {
          return current;
        }
        return {
          ...current,
          runtime_prompts: agentRuntimePromptsFromDefaults(defaultsPayload),
        };
      });
      setState("success");
    } catch (error) {
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : t("catalogControl.feedback.loadFailed"));
    }
  }, [t, token]);

  useEffect(() => {
    void loadCatalogState();
  }, [loadCatalogState]);

  useEffect(() => {
    if (!token) {
      setAgentPromptPreview("");
      return;
    }

    const requestId = promptPreviewRequestId.current + 1;
    promptPreviewRequestId.current = requestId;
    setAgentPromptPreviewLoading(true);
    const timeout = window.setTimeout(() => {
      const payload: CatalogAgentMutationInput = {
        id: agentForm.id || undefined,
        visibility: agentForm.visibility,
        publish: agentForm.publish,
        name: agentForm.name,
        description: agentForm.description,
        instructions: agentForm.instructions,
        runtime_prompts: {
          retrieval_context: agentForm.runtime_prompts.retrieval_context,
        },
        default_model_ref: agentForm.default_model_ref,
        tool_refs: agentForm.tool_refs,
        mcp_server_refs: agentForm.mcp_server_refs,
        agent_domain: agentForm.agent_domain,
        runtime_constraints: agentForm.runtime_constraints,
      };
      void previewCatalogAgentPrompt(payload, token)
        .then((preview) => {
          if (promptPreviewRequestId.current === requestId) {
            setAgentPromptPreview(preview.prompt_preview.text);
          }
        })
        .catch(() => {
          if (promptPreviewRequestId.current === requestId) {
            setAgentPromptPreview("");
          }
        })
        .finally(() => {
          if (promptPreviewRequestId.current === requestId) {
            setAgentPromptPreviewLoading(false);
          }
        });
    }, 200);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [agentForm, token]);

  async function handleAgentValidate(agentId: string): Promise<void> {
    if (!token) {
      return;
    }
    setValidatingAgentId(agentId);
    try {
      const result = await validateCatalogAgent(agentId, token);
      setAgentValidationResults((current) => ({ ...current, [agentId]: result }));
      showSuccessFeedback(t("catalogControl.feedback.agentValidated", { name: result.agent.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.validationFailed"));
    } finally {
      setValidatingAgentId("");
    }
  }

  async function handleToolValidate(toolId: string): Promise<void> {
    if (!token) {
      return;
    }
    setValidatingToolId(toolId);
    try {
      const result = await validateCatalogTool(toolId, token);
      setToolValidationResults((current) => ({ ...current, [toolId]: result }));
      showSuccessFeedback(t("catalogControl.feedback.toolValidated", { name: result.tool.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.validationFailed"));
    } finally {
      setValidatingToolId("");
    }
  }

  async function handleMcpValidate(mcpServerId: string): Promise<void> {
    if (!token) {
      return;
    }
    setValidatingMcpServerId(mcpServerId);
    try {
      const result = await validateCatalogMcpServer(mcpServerId, token);
      setMcpValidationResults((current) => ({ ...current, [mcpServerId]: result }));
      showSuccessFeedback(t("catalogControl.feedback.mcpValidated", { name: result.mcp_server.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.validationFailed"));
    } finally {
      setValidatingMcpServerId("");
    }
  }

  async function handleAgentSubmit(): Promise<CatalogAgent | null> {
    if (!token) {
      return null;
    }
    setSavingAgent(true);
    try {
      const payload: CatalogAgentMutationInput = {
        id: agentForm.id || undefined,
        visibility: agentForm.visibility,
        publish: agentForm.publish,
        name: agentForm.name,
        description: agentForm.description,
        instructions: agentForm.instructions,
        runtime_prompts: {
          retrieval_context: agentForm.runtime_prompts.retrieval_context,
        },
        default_model_ref: agentForm.default_model_ref?.trim() ? agentForm.default_model_ref.trim() : null,
        tool_refs: agentForm.tool_refs,
        mcp_server_refs: agentForm.mcp_server_refs,
        agent_domain: agentForm.agent_domain,
        runtime_constraints: agentForm.runtime_constraints,
      };
      const saved =
        agentForm.mode === "create"
          ? await createCatalogAgent(payload, token)
          : await updateCatalogAgent(agentForm.agentId, payload, token);
      setAgentForm(buildAgentForm(saved));
      await loadCatalogState();
      showSuccessFeedback(
        t(agentForm.mode === "create" ? "catalogControl.feedback.agentCreated" : "catalogControl.feedback.agentUpdated", {
          name: saved.spec.name,
        }),
      );
      return saved;
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
      return null;
    } finally {
      setSavingAgent(false);
    }
  }

  async function handleAgentDelete(agent: CatalogAgent): Promise<boolean> {
    if (!token) {
      return false;
    }
    setDeletingAgentId(agent.id);
    try {
      await deleteCatalogAgent(agent.id, token);
      await loadCatalogState();
      showSuccessFeedback(t("catalogControl.feedback.agentDeleted", { name: agent.spec.name }));
      return true;
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.deleteFailed"));
      return false;
    } finally {
      setDeletingAgentId("");
    }
  }

  async function handleToolSubmit(): Promise<CatalogTool | null> {
    if (!token) {
      return null;
    }
    setSavingTool(true);
    try {
      const inputSchema = parseJsonObject(
        toolForm.inputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.inputSchema") }),
      );
      const outputSchema = parseJsonObject(
        toolForm.outputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.outputSchema") }),
      );
      const safetyPolicy = parseJsonObject(
        toolForm.safetyPolicyText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.safetyPolicy") }),
      );
      const executionConfig = parseJsonObject(
        toolForm.executionConfigText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.executionConfig") }),
      );
      const permissions = parseJsonObject(
        toolForm.permissionsText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.permissions") }),
      );
      if (!toolForm.execution_backend) {
        throw new Error(t("catalogControl.feedback.executionBackendRequired"));
      }

      const payload: CatalogToolMutationInput = {
        id: toolForm.id || undefined,
        visibility: toolForm.visibility,
        publish: toolForm.publish,
        name: toolForm.name,
        description: toolForm.description,
        input_schema: inputSchema,
        output_schema: outputSchema,
        safety_policy: safetyPolicy,
        offline_compatible: toolForm.offline_compatible,
        execution_backend: toolForm.execution_backend,
        execution_config: executionConfig,
        permissions,
      };
      const saved =
        toolForm.mode === "create"
          ? await createCatalogTool(payload, token)
          : await updateCatalogTool(toolForm.toolId, payload, token);
      setToolForm(buildToolForm(saved));
      await loadCatalogState();
      showSuccessFeedback(
        t(toolForm.mode === "create" ? "catalogControl.feedback.toolCreated" : "catalogControl.feedback.toolUpdated", {
          name: saved.spec.name,
        }),
      );
      return saved;
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
      return null;
    } finally {
      setSavingTool(false);
    }
  }

  async function handleMcpSubmit(): Promise<CatalogMcpServer | null> {
    if (!token) {
      return null;
    }
    setSavingMcpServer(true);
    try {
      const inputSchema = parseJsonObject(
        mcpServerForm.inputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.mcp.inputSchema") }),
      );
      const outputSchema = parseJsonObject(
        mcpServerForm.outputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.mcp.outputSchema") }),
      );
      const payload: CatalogMcpServerMutationInput = {
        id: mcpServerForm.id || undefined,
        visibility: mcpServerForm.visibility,
        publish: mcpServerForm.publish,
        name: mcpServerForm.name,
        slug: mcpServerForm.slug,
        description: mcpServerForm.description,
        backing_tool_id: mcpServerForm.backing_tool_id,
        exposed_tool_name: mcpServerForm.exposed_tool_name,
        input_schema: inputSchema,
        output_schema: outputSchema,
        metadata: {
          ...mcpServerForm.metadata,
          capabilities: textToTags(mcpServerForm.capabilitiesText),
        },
        authorization_policy: {
          agent_ids: textToList(mcpServerForm.agentIdsText),
          agent_domains: textToList(mcpServerForm.agentDomainsText),
          agent_roles: textToList(mcpServerForm.agentRolesText),
          user_roles: textToList(mcpServerForm.userRolesText),
          user_ids: textToList(mcpServerForm.userIdsText),
          user_group_ids: textToList(mcpServerForm.userGroupIdsText),
        },
        enabled: mcpServerForm.enabled,
      };
      const saved =
        mcpServerForm.mode === "create"
          ? await createCatalogMcpServer(payload, token)
          : await updateCatalogMcpServer(mcpServerForm.mcpServerId, payload, token);
      setMcpServerForm(buildMcpServerForm(saved));
      await loadCatalogState();
      showSuccessFeedback(
        t(mcpServerForm.mode === "create" ? "catalogControl.feedback.mcpCreated" : "catalogControl.feedback.mcpUpdated", {
          name: saved.spec.name,
        }),
      );
      return saved;
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
      return null;
    } finally {
      setSavingMcpServer(false);
    }
  }

  async function handleMcpDelete(server: CatalogMcpServer): Promise<void> {
    if (!token) {
      return;
    }
    try {
      await deleteCatalogMcpServer(server.id, token);
      await loadCatalogState();
      showSuccessFeedback(t("catalogControl.feedback.mcpDeleted", { name: server.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.deleteFailed"));
    }
  }

  async function handleMcpToggle(server: CatalogMcpServer): Promise<void> {
    if (!token) {
      return;
    }
    try {
      const saved = await setCatalogMcpServerEnabled(server.id, !server.spec.enabled, token);
      setMcpServers((current) => current.map((item) => (item.id === saved.id ? saved : item)));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
    }
  }

  return {
    state,
    errorMessage,
    agents,
    tools,
    mcpServers,
    models,
    toolCreationOptions,
    mcpCreationOptions,
    agentForm,
    setAgentForm,
    toolForm,
    setToolForm,
    mcpServerForm,
    setMcpServerForm,
    toolTestForm: toolTesting.toolTestForm,
    setToolTestForm: toolTesting.setToolTestForm,
    agentValidationResults,
    toolValidationResults,
    mcpValidationResults,
    toolTestResult: toolTesting.toolTestResult,
    toolTestError: toolTesting.toolTestError,
    validatingAgentId,
    validatingToolId,
    validatingMcpServerId,
    deletingAgentId,
    agentPromptPreview,
    agentPromptPreviewLoading,
    testingToolId: toolTesting.testingToolId,
    savingAgent,
    savingTool,
    savingMcpServer,
    loadCatalogState,
    handleAgentValidate,
    handleAgentDelete,
    handleToolValidate,
    handleMcpValidate,
    handleAgentSubmit,
    handleToolSubmit,
    handleMcpSubmit,
    handleMcpDelete,
    handleMcpToggle,
    handleToolTest: toolTesting.handleToolTest,
    openAgentEditor: (agent: CatalogAgent) => setAgentForm(buildAgentForm(agent)),
    openToolEditor: (tool: CatalogTool) => setToolForm(buildToolForm(tool)),
    openMcpEditor: (server: CatalogMcpServer) => setMcpServerForm(buildMcpServerForm(server)),
    openToolTester: toolTesting.openToolTester,
    resetAgentForm: () => setAgentForm(buildDefaultAgentForm(catalogDefaultsRef.current)),
    resetToolForm: () => setToolForm(DEFAULT_TOOL_FORM),
    resetMcpServerForm: () => setMcpServerForm(DEFAULT_MCP_SERVER_FORM),
    resetToolTester: toolTesting.resetToolTester,
    publishedAgents: agents.filter((agent) => agent.published).length,
    publishedTools: tools.filter((tool) => tool.published).length,
    enabledMcpServers: mcpServers.filter((server) => server.spec.enabled).length,
  };
}
