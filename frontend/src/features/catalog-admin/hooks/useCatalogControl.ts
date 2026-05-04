import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createCatalogAgent,
  createCatalogTool,
  deleteCatalogAgent,
  getCatalogDefaults,
  listCatalogAgents,
  listCatalogTools,
  previewCatalogAgentPrompt,
  type CatalogAgent,
  type CatalogAgentMutationInput,
  type CatalogAgentValidation,
  type CatalogDefaults,
  type CatalogTool,
  type CatalogToolMutationInput,
  type CatalogToolValidation,
  updateCatalogAgent,
  updateCatalogTool,
  validateCatalogAgent,
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

export type ToolFormState = CatalogToolMutationInput & {
  mode: FormMode;
  toolId: string;
  inputSchemaText: string;
  outputSchemaText: string;
  safetyPolicyText: string;
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
  transport: "mcp",
  connection_profile_ref: "default",
  tool_name: "",
  input_schema: {},
  output_schema: {},
  safety_policy: {},
  offline_compatible: false,
  inputSchemaText: "{}",
  outputSchemaText: "{}",
  safetyPolicyText: "{}",
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
    transport: tool.spec.transport,
    connection_profile_ref: "default",
    tool_name: tool.spec.tool_name,
    input_schema: tool.spec.input_schema,
    output_schema: tool.spec.output_schema,
    safety_policy: tool.spec.safety_policy,
    offline_compatible: tool.spec.offline_compatible,
    inputSchemaText: stringifyJson(tool.spec.input_schema),
    outputSchemaText: stringifyJson(tool.spec.output_schema),
    safetyPolicyText: stringifyJson(tool.spec.safety_policy),
  };
}

export function useCatalogControl(token: string) {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [state, setState] = useState<CatalogLoadState>("idle");
  const [agents, setAgents] = useState<CatalogAgent[]>([]);
  const [tools, setTools] = useState<CatalogTool[]>([]);
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [agentForm, setAgentForm] = useState<AgentFormState>(() => buildDefaultAgentForm(null));
  const [toolForm, setToolForm] = useState<ToolFormState>(DEFAULT_TOOL_FORM);
  const [agentValidationResults, setAgentValidationResults] = useState<Record<string, CatalogAgentValidation>>({});
  const [toolValidationResults, setToolValidationResults] = useState<Record<string, CatalogToolValidation>>({});
  const [validatingAgentId, setValidatingAgentId] = useState("");
  const [validatingToolId, setValidatingToolId] = useState("");
  const [deletingAgentId, setDeletingAgentId] = useState("");
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingTool, setSavingTool] = useState(false);
  const [agentPromptPreview, setAgentPromptPreview] = useState("");
  const [agentPromptPreviewLoading, setAgentPromptPreviewLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const catalogDefaultsRef = useRef<CatalogDefaults | null>(null);
  const promptPreviewRequestId = useRef(0);
  const toolTesting = useCatalogToolTesting(token);

  const loadCatalogState = useCallback(async (): Promise<void> => {
    if (!token) {
      setState("error");
      setErrorMessage(t("catalogControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [defaultsPayload, agentsPayload, toolsPayload, modelsPayload] = await Promise.all([
        getCatalogDefaults(token),
        listCatalogAgents(token),
        listCatalogTools(token),
        listEnabledModels(token),
      ]);
      const previousDefaults = catalogDefaultsRef.current;
      catalogDefaultsRef.current = defaultsPayload;
      setAgents(agentsPayload);
      setTools(toolsPayload);
      setModels(modelsPayload);
      setAgentForm((current) => {
        if (current.mode !== "create") {
          return current;
        }
        const currentRetrievalContext = current.runtime_prompts.retrieval_context.trim();
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

      const payload: CatalogToolMutationInput = {
        id: toolForm.id || undefined,
        visibility: toolForm.visibility,
        publish: toolForm.publish,
        name: toolForm.name,
        description: toolForm.description,
        transport: toolForm.transport,
        connection_profile_ref: "default",
        tool_name: toolForm.tool_name,
        input_schema: inputSchema,
        output_schema: outputSchema,
        safety_policy: safetyPolicy,
        offline_compatible: toolForm.offline_compatible,
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

  return {
    state,
    errorMessage,
    agents,
    tools,
    models,
    agentForm,
    setAgentForm,
    toolForm,
    setToolForm,
    toolTestForm: toolTesting.toolTestForm,
    setToolTestForm: toolTesting.setToolTestForm,
    agentValidationResults,
    toolValidationResults,
    toolTestResult: toolTesting.toolTestResult,
    toolTestError: toolTesting.toolTestError,
    validatingAgentId,
    validatingToolId,
    deletingAgentId,
    agentPromptPreview,
    agentPromptPreviewLoading,
    testingToolId: toolTesting.testingToolId,
    savingAgent,
    savingTool,
    loadCatalogState,
    handleAgentValidate,
    handleAgentDelete,
    handleToolValidate,
    handleAgentSubmit,
    handleToolSubmit,
    handleToolTest: toolTesting.handleToolTest,
    openAgentEditor: (agent: CatalogAgent) => setAgentForm(buildAgentForm(agent)),
    openToolEditor: (tool: CatalogTool) => setToolForm(buildToolForm(tool)),
    openToolTester: toolTesting.openToolTester,
    resetAgentForm: () => setAgentForm(buildDefaultAgentForm(catalogDefaultsRef.current)),
    resetToolForm: () => setToolForm(DEFAULT_TOOL_FORM),
    resetToolTester: toolTesting.resetToolTester,
    publishedAgents: agents.filter((agent) => agent.published).length,
    publishedTools: tools.filter((tool) => tool.published).length,
  };
}
