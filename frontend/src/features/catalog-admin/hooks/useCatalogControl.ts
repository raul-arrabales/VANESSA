import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createCatalogAgent,
  createCatalogTool,
  listCatalogAgents,
  listCatalogTools,
  testCatalogTool,
  type CatalogAgent,
  type CatalogAgentMutationInput,
  type CatalogAgentValidation,
  type CatalogTool,
  type CatalogToolMutationInput,
  type CatalogToolTestResult,
  type CatalogToolValidation,
  updateCatalogAgent,
  updateCatalogTool,
  validateCatalogAgent,
  validateCatalogTool,
} from "../../../api/catalog";
import { listEnabledModels, type ModelCatalogItem } from "../../../api/modelops";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

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

export type ToolTestFormState = {
  toolId: string;
  inputText: string;
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

export const DEFAULT_TOOL_TEST_FORM: ToolTestFormState = {
  toolId: "",
  inputText: "{}",
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

function buildSampleValueFromSchema(schema: unknown, propertyName = ""): unknown {
  if (!schema || typeof schema !== "object" || Array.isArray(schema)) {
    if (propertyName === "query") {
      return "OpenAI platform runtime";
    }
    if (propertyName === "code") {
      return "print('Hello from VANESSA')";
    }
    if (propertyName === "timeout_seconds" || propertyName === "top_k") {
      return 3;
    }
    return "";
  }

  const schemaObject = schema as Record<string, unknown>;
  const schemaType = String(schemaObject.type ?? "").trim().toLowerCase();
  const enumValues = Array.isArray(schemaObject.enum) ? schemaObject.enum : [];
  if (enumValues.length > 0) {
    return enumValues[0];
  }

  if (schemaType === "object" || schemaObject.properties) {
    const properties = schemaObject.properties && typeof schemaObject.properties === "object"
      ? schemaObject.properties as Record<string, unknown>
      : {};
    const required = Array.isArray(schemaObject.required)
      ? schemaObject.required.filter((item): item is string => typeof item === "string")
      : [];
    const propertyKeys = required.length > 0 ? required : Object.keys(properties).slice(0, 3);
    const result: Record<string, unknown> = {};
    for (const key of propertyKeys) {
      if (!(key in properties)) {
        continue;
      }
      result[key] = buildSampleValueFromSchema(properties[key], key);
    }
    return result;
  }

  if (schemaType === "array") {
    return [buildSampleValueFromSchema(schemaObject.items, propertyName)];
  }

  if (schemaType === "integer" || schemaType === "number") {
    const minimum = schemaObject.minimum;
    return typeof minimum === "number" ? minimum : 1;
  }

  if (schemaType === "boolean") {
    return false;
  }

  if (propertyName === "query") {
    return "OpenAI platform runtime";
  }
  if (propertyName === "code") {
    return "print('Hello from VANESSA')";
  }
  if (propertyName === "tool_name") {
    return "example_tool";
  }
  return "example";
}

function buildSampleToolInput(tool: CatalogTool): Record<string, unknown> {
  if (tool.id === "tool.web_search" || tool.spec.tool_name === "web_search") {
    return {
      query: "OpenAI platform runtime",
      top_k: 3,
    };
  }

  if (tool.id === "tool.python_exec" || tool.spec.tool_name === "python_exec") {
    return {
      code: "numbers = input_payload.get('numbers', [1, 2, 3])\nresult = sum(numbers)\nprint(f'Sum: {result}')",
      input: {
        numbers: [1, 2, 3],
      },
      timeout_seconds: 5,
    };
  }

  return buildSampleValueFromSchema(tool.spec.input_schema) as Record<string, unknown>;
}

export function buildToolTestForm(tool: CatalogTool): ToolTestFormState {
  return {
    toolId: tool.id,
    inputText: stringifyJson(buildSampleToolInput(tool)),
  };
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
  const [agentForm, setAgentForm] = useState<AgentFormState>(DEFAULT_AGENT_FORM);
  const [toolForm, setToolForm] = useState<ToolFormState>(DEFAULT_TOOL_FORM);
  const [toolTestForm, setToolTestForm] = useState<ToolTestFormState>(DEFAULT_TOOL_TEST_FORM);
  const [agentValidationResults, setAgentValidationResults] = useState<Record<string, CatalogAgentValidation>>({});
  const [toolValidationResults, setToolValidationResults] = useState<Record<string, CatalogToolValidation>>({});
  const [toolTestResult, setToolTestResult] = useState<CatalogToolTestResult | null>(null);
  const [toolTestError, setToolTestError] = useState("");
  const [validatingAgentId, setValidatingAgentId] = useState("");
  const [validatingToolId, setValidatingToolId] = useState("");
  const [testingToolId, setTestingToolId] = useState("");
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingTool, setSavingTool] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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

  async function handleToolTest(): Promise<CatalogToolTestResult | null> {
    if (!token || !toolTestForm.toolId) {
      return null;
    }
    setTestingToolId(toolTestForm.toolId);
    setToolTestError("");
    try {
      const input = parseJsonObject(
        toolTestForm.inputText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.toolTest.input") }),
      );
      const result = await testCatalogTool(toolTestForm.toolId, input, token);
      setToolTestResult(result);
      return result;
    } catch (error) {
      setToolTestResult(null);
      const message = error instanceof Error ? error.message : t("catalogControl.feedback.toolTestFailed");
      setToolTestError(message);
      showErrorFeedback(error, t("catalogControl.feedback.toolTestFailed"));
      return null;
    } finally {
      setTestingToolId("");
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
    toolTestForm,
    setToolTestForm,
    agentValidationResults,
    toolValidationResults,
    toolTestResult,
    toolTestError,
    validatingAgentId,
    validatingToolId,
    testingToolId,
    savingAgent,
    savingTool,
    loadCatalogState,
    handleAgentValidate,
    handleToolValidate,
    handleAgentSubmit,
    handleToolSubmit,
    handleToolTest,
    openAgentEditor: (agent: CatalogAgent) => setAgentForm(buildAgentForm(agent)),
    openToolEditor: (tool: CatalogTool) => setToolForm(buildToolForm(tool)),
    openToolTester: (tool: CatalogTool) => {
      setToolTestForm(buildToolTestForm(tool));
      setToolTestResult(null);
      setToolTestError("");
    },
    resetAgentForm: () => setAgentForm(DEFAULT_AGENT_FORM),
    resetToolForm: () => setToolForm(DEFAULT_TOOL_FORM),
    resetToolTester: () => {
      setToolTestForm(DEFAULT_TOOL_TEST_FORM);
      setToolTestResult(null);
      setToolTestError("");
    },
    publishedAgents: agents.filter((agent) => agent.published).length,
    publishedTools: tools.filter((tool) => tool.published).length,
  };
}
