import type { AgentProject, AgentProjectMutationInput, AgentProjectVisibility, WorkflowAction, WorkflowDefinition } from "../../api/agentProjects";
import type { CatalogDefaults } from "../../api/catalog";
import type { PreviewableAssistantExperience } from "../ai-shared/assistantExperience";

export type AgentProjectFormState = {
  id: string;
  visibility: AgentProjectVisibility;
  name: string;
  description: string;
  instructions: string;
  retrievalContext: string;
  defaultModelRef: string;
  agentType: "" | "workflow" | "planner" | "react";
  channelType: "" | "vanessa_webapp";
  interfaceType: "" | "chat";
  agentDomain: string;
  workflowActions: WorkflowAction[];
  toolRefsText: string;
  mcpServerRefsText: string;
  workflowDefinitionText: string;
  toolPolicyText: string;
  internetRequired: boolean;
  sandboxRequired: boolean;
};

export type AgentProjectPreview = PreviewableAssistantExperience;

export const DEFAULT_WORKFLOW_AGENT_DESCRIPTION = "Executes a deterministic MCP workflow in the Vanessa WebApp chat.";
export const DEFAULT_WORKFLOW_TOOL_POLICY_TEXT = "{\n  \"allow_user_tools\": false\n}";
export const EMPTY_WORKFLOW_DEFINITION: WorkflowDefinition = { version: 2, actions: [] };

function normalizeId(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeName(value: string): string {
  return value.trim().toLowerCase();
}

function nextAvailableNumberedValue(prefix: string, existingValues: string[], normalize: (value: string) => string, separator: "-" | " "): string {
  const join = (counter: number) => `${prefix}${separator}${counter}`;
  const used = new Set(existingValues.map(normalize).filter(Boolean));
  let counter = 1;
  while (used.has(normalize(join(counter)))) {
    counter += 1;
  }
  return join(counter);
}

function nextAvailableNumberedName(base: string, existingNames: string[]): string {
  const used = new Set(existingNames.map(normalizeName).filter(Boolean));
  let counter = 1;
  while (used.has(normalizeName(`${base} ${counter}`))) {
    counter += 1;
  }
  return `${base} ${counter}`;
}

export function buildDefaultAgentProjectForm(
  defaults: CatalogDefaults | null,
  options: {
    existingProjectIds?: string[];
    existingAgentNames?: string[];
  } = {},
): AgentProjectFormState {
  const baseId = "workflow-agent";
  const baseName = "Workflow Agent";
  const id = nextAvailableNumberedValue(baseId, options.existingProjectIds ?? [], normalizeId, "-");
  const name = nextAvailableNumberedName(baseName, options.existingAgentNames ?? []);
  return {
    id,
    visibility: "private",
    name,
    description: DEFAULT_WORKFLOW_AGENT_DESCRIPTION,
    instructions: "",
    retrievalContext: defaults?.agent.runtime_prompts.retrieval_context ?? "",
    defaultModelRef: "",
    agentType: "workflow",
    channelType: "vanessa_webapp",
    interfaceType: "chat",
    agentDomain: "default",
    workflowActions: [],
    toolRefsText: "",
    mcpServerRefsText: "",
    workflowDefinitionText: JSON.stringify(EMPTY_WORKFLOW_DEFINITION, null, 2),
    toolPolicyText: DEFAULT_WORKFLOW_TOOL_POLICY_TEXT,
    internetRequired: false,
    sandboxRequired: false,
  };
}

export const DEFAULT_AGENT_PROJECT_FORM: AgentProjectFormState = buildDefaultAgentProjectForm(null);

export function buildGuidedUserAgentCreateForm(
  defaults: CatalogDefaults | null,
  options: {
    existingProjectIds?: string[];
    existingAgentNames?: string[];
    agentType?: AgentProjectFormState["agentType"];
  } = {},
): AgentProjectFormState {
  const selectedAgentType = options.agentType ?? "";
  if (selectedAgentType === "workflow") {
    const workflowDefaults = buildDefaultAgentProjectForm(defaults, options);
    return {
      ...workflowDefaults,
      agentType: "workflow",
      channelType: "vanessa_webapp",
      interfaceType: "chat",
    };
  }

  return {
    id: "",
    visibility: "private",
    name: "",
    description: "",
    instructions: "",
    retrievalContext: defaults?.agent.runtime_prompts.retrieval_context ?? "",
    defaultModelRef: "",
    agentType: "",
    channelType: "",
    interfaceType: "",
    agentDomain: "default",
    workflowActions: [],
    toolRefsText: "",
    mcpServerRefsText: "",
    workflowDefinitionText: JSON.stringify(EMPTY_WORKFLOW_DEFINITION, null, 2),
    toolPolicyText: DEFAULT_WORKFLOW_TOOL_POLICY_TEXT,
    internetRequired: false,
    sandboxRequired: false,
  };
}

export function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
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

export function buildAgentProjectForm(project: AgentProject): AgentProjectFormState {
  return {
    id: project.id,
    visibility: project.visibility,
    name: project.spec.name,
    description: project.spec.description,
    instructions: project.spec.instructions,
    retrievalContext: project.spec.runtime_prompts.retrieval_context,
    defaultModelRef: project.spec.default_model_ref ?? "",
    agentType: project.spec.agent_type,
    channelType: project.spec.channel_type,
    interfaceType: project.spec.interface_type,
    agentDomain: project.spec.agent_domain ?? "default",
    workflowActions: normalizeWorkflowActions(project.spec.workflow_definition),
    toolRefsText: JSON.stringify(project.spec.tool_refs, null, 2),
    mcpServerRefsText: JSON.stringify(project.spec.mcp_server_refs ?? [], null, 2),
    workflowDefinitionText: JSON.stringify(project.spec.workflow_definition ?? EMPTY_WORKFLOW_DEFINITION, null, 2),
    toolPolicyText: JSON.stringify(project.spec.tool_policy, null, 2),
    internetRequired: project.spec.runtime_constraints.internet_required,
    sandboxRequired: project.spec.runtime_constraints.sandbox_required,
  };
}

function normalizeWorkflowActions(workflowDefinition: unknown): WorkflowAction[] {
  if (!workflowDefinition || typeof workflowDefinition !== "object" || Array.isArray(workflowDefinition)) {
    return [];
  }
  const definition = workflowDefinition as Record<string, unknown>;
  if (definition.version !== 2 || !Array.isArray(definition.actions)) {
    return [];
  }
  return definition.actions.filter((item): item is WorkflowAction => Boolean(item && typeof item === "object" && "type" in item));
}

function workflowDefinitionFromForm(form: AgentProjectFormState): WorkflowDefinition {
  return {
    version: 2,
    actions: form.workflowActions.map((action, index) => ({
      ...action,
      id: String(action.id || `${action.type}_${index + 1}`),
      name: String(action.name || action.type.replace(/_/g, " ")).trim() || action.type,
    })),
  };
}

function mcpServerRefsFromWorkflow(actions: WorkflowAction[]): string[] {
  return Array.from(new Set(actions
    .filter((action): action is Extract<WorkflowAction, { type: "mcp_tool" }> => action.type === "mcp_tool")
    .map((action) => action.mcp_server_slug.trim())
    .filter(Boolean)));
}

export function toAgentProjectMutationInput(
  form: AgentProjectFormState,
  options: {
    includeId: boolean;
    invalidWorkflowMessage: string;
    invalidToolPolicyMessage: string;
  },
): AgentProjectMutationInput {
  const { includeId, invalidToolPolicyMessage } = options;
  const id = form.id.trim();
  const agentType = (form.agentType || "workflow") as "workflow" | "planner" | "react";
  const channelType = (form.channelType || "vanessa_webapp") as "vanessa_webapp";
  const interfaceType = (form.interfaceType || "chat") as "chat";
  const workflowDefinition = workflowDefinitionFromForm(form);
  return {
    ...(includeId && id ? { id } : {}),
    visibility: form.visibility,
    name: form.name.trim(),
    description: form.description.trim(),
    instructions: agentType === "workflow" ? "" : form.instructions.trim(),
    runtime_prompts: {
      retrieval_context: form.retrievalContext.trim(),
    },
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: [],
    mcp_server_refs: mcpServerRefsFromWorkflow(workflowDefinition.actions),
    agent_domain: form.agentDomain.trim() || "default",
    agent_type: agentType,
    channel_type: channelType,
    interface_type: interfaceType,
    workflow_definition: workflowDefinition,
    tool_policy: parseJsonObject(form.toolPolicyText, invalidToolPolicyMessage),
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
  };
}

export function buildAgentProjectPreview(projectId: string, form: AgentProjectFormState): AgentProjectPreview {
  const agentType = (form.agentType || "workflow") as "workflow" | "planner" | "react";
  const channelType = (form.channelType || "vanessa_webapp") as "vanessa_webapp";
  const interfaceType = (form.interfaceType || "chat") as "chat";
  const defaultModelRef = String(form.defaultModelRef ?? "").trim();
  const agentDomain = String(form.agentDomain ?? "").trim();
  const workflowDefinition = workflowDefinitionFromForm(form);

  return {
    assistant_ref: `agent.project.${projectId || "draft"}`,
    playground_kind: "chat",
    default_model_ref: defaultModelRef || null,
    tool_refs: [],
    mcp_server_refs: mcpServerRefsFromWorkflow(workflowDefinition.actions),
    agent_domain: agentDomain || "default",
    agent_type: agentType,
    channel_type: channelType,
    interface_type: interfaceType,
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
    workflow_definition: workflowDefinition,
  };
}
