import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createCatalogAgent,
  createCatalogTool,
  deleteCatalogAgent,
  listCatalogAgents,
  listCatalogTools,
  type CatalogAgent,
  type CatalogAgentMutationInput,
  type CatalogAgentValidation,
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

export const DEFAULT_RETRIEVAL_CONTEXT_PROMPT = [
  "Use the following retrieved context if it is relevant to the user's request.",
  "When you use retrieved context, cite the supporting reference inline with bracketed numeric citations such as [1] or [1, 2].",
  "Do not cite a reference unless it supports the sentence that uses the citation.",
].join("\n");

const RETRIEVAL_CONTEXT_PREVIEW = [
  "Reference [1] title={retrieved title} file={retrieved file}",
  "Chunk id={retrieved chunk id} metadata={retrieved metadata}",
  "{retrieved text}",
].join("\n");

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

export const DEFAULT_AGENT_FORM: AgentFormState = {
  mode: "create",
  agentId: "",
  id: "",
  visibility: "private",
  publish: false,
  name: "",
  description: "",
  instructions: "",
  runtime_prompts: {
    retrieval_context: DEFAULT_RETRIEVAL_CONTEXT_PROMPT,
  },
  default_model_ref: null,
  tool_refs: [],
  runtime_constraints: {
    internet_required: false,
    sandbox_required: false,
  },
};

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
      retrieval_context: agent.spec.runtime_prompts?.retrieval_context?.trim() || DEFAULT_RETRIEVAL_CONTEXT_PROMPT,
    },
    default_model_ref: agent.spec.default_model_ref,
    tool_refs: agent.spec.tool_refs,
    runtime_constraints: {
      internet_required: agent.spec.runtime_constraints.internet_required,
      sandbox_required: agent.spec.runtime_constraints.sandbox_required,
    },
  };
}

export function buildAgentSystemPromptPreview(form: AgentFormState): string {
  const sections: string[] = [];
  const instructions = form.instructions.trim();
  if (instructions) {
    sections.push(["System message: agent instructions", instructions].join("\n"));
  }

  const retrievalContext = form.runtime_prompts.retrieval_context.trim();
  if (retrievalContext) {
    sections.push(["System message: retrieval context", retrievalContext, RETRIEVAL_CONTEXT_PREVIEW].join("\n\n"));
  }

  return sections.join("\n\n---\n\n");
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
  const [agentForm, setAgentForm] = useState<AgentFormState>(DEFAULT_AGENT_FORM);
  const [toolForm, setToolForm] = useState<ToolFormState>(DEFAULT_TOOL_FORM);
  const [agentValidationResults, setAgentValidationResults] = useState<Record<string, CatalogAgentValidation>>({});
  const [toolValidationResults, setToolValidationResults] = useState<Record<string, CatalogToolValidation>>({});
  const [validatingAgentId, setValidatingAgentId] = useState("");
  const [validatingToolId, setValidatingToolId] = useState("");
  const [deletingAgentId, setDeletingAgentId] = useState("");
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingTool, setSavingTool] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
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
      const [agentsPayload, toolsPayload, modelsPayload] = await Promise.all([
        listCatalogAgents(token),
        listCatalogTools(token),
        listEnabledModels(token),
      ]);
      setAgents(agentsPayload);
      setTools(toolsPayload);
      setModels(modelsPayload);
      setState("success");
    } catch (error) {
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : t("catalogControl.feedback.loadFailed"));
    }
  }, [t, token]);

  useEffect(() => {
    void loadCatalogState();
  }, [loadCatalogState]);

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
    resetAgentForm: () => setAgentForm(DEFAULT_AGENT_FORM),
    resetToolForm: () => setToolForm(DEFAULT_TOOL_FORM),
    resetToolTester: toolTesting.resetToolTester,
    publishedAgents: agents.filter((agent) => agent.published).length,
    publishedTools: tools.filter((tool) => tool.published).length,
  };
}
