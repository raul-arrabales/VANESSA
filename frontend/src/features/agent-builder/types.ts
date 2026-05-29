import type { AgentProject, AgentProjectMutationInput, AgentProjectVisibility } from "../../api/agentProjects";
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
  agentType: "workflow" | "planner" | "react";
  channelType: "vanessa_webapp";
  interfaceType: "chat";
  agentDomain: string;
  selectedMcpServerSlug: string;
  selectedToolName: string;
  stepName: string;
  stepArgumentsText: string;
  toolPolicyText: string;
  internetRequired: boolean;
  sandboxRequired: boolean;
};

export type AgentProjectPreview = PreviewableAssistantExperience;

const DEFAULT_WORKFLOW_AGENT_DESCRIPTION = "Executes a deterministic MCP workflow in the Vanessa WebApp chat.";

function normalizeId(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeName(value: string): string {
  return value.trim().toLowerCase();
}

function nextAvailableSuffixedValue(base: string, existingValues: string[], normalize: (value: string) => string): string {
  const used = new Set(existingValues.map(normalize).filter(Boolean));
  if (!used.has(normalize(base))) {
    return base;
  }
  let counter = 2;
  while (used.has(normalize(`${base}-${counter}`))) {
    counter += 1;
  }
  return `${base}-${counter}`;
}

function nextAvailableSuffixedName(base: string, existingNames: string[]): string {
  const used = new Set(existingNames.map(normalizeName).filter(Boolean));
  if (!used.has(normalizeName(base))) {
    return base;
  }
  let counter = 2;
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
  const id = nextAvailableSuffixedValue(baseId, options.existingProjectIds ?? [], normalizeId);
  const name = nextAvailableSuffixedName(baseName, options.existingAgentNames ?? []);
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
    selectedMcpServerSlug: "",
    selectedToolName: "",
    stepName: "",
    stepArgumentsText: "{}",
    toolPolicyText: "{\n  \"allow_user_tools\": false\n}",
    internetRequired: false,
    sandboxRequired: false,
  };
}

export const DEFAULT_AGENT_PROJECT_FORM: AgentProjectFormState = buildDefaultAgentProjectForm(null);

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
  const workflowSteps = Array.isArray(project.spec.workflow_definition?.steps) ? project.spec.workflow_definition.steps : [];
  const firstWorkflowStep = workflowSteps[0];
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
    selectedMcpServerSlug: firstWorkflowStep?.mcp_server_slug ?? "",
    selectedToolName: firstWorkflowStep?.exposed_tool_name ?? "",
    stepName: firstWorkflowStep?.name ?? "",
    stepArgumentsText: JSON.stringify(firstWorkflowStep?.arguments ?? {}, null, 2),
    toolPolicyText: JSON.stringify(project.spec.tool_policy, null, 2),
    internetRequired: project.spec.runtime_constraints.internet_required,
    sandboxRequired: project.spec.runtime_constraints.sandbox_required,
  };
}

export function toAgentProjectMutationInput(
  form: AgentProjectFormState,
  options: {
    includeId: boolean;
    invalidWorkflowMessage: string;
    invalidToolPolicyMessage: string;
  },
): AgentProjectMutationInput {
  const { includeId, invalidWorkflowMessage, invalidToolPolicyMessage } = options;
  const id = form.id.trim();
  const selectedMcpServerSlug = String(form.selectedMcpServerSlug ?? "").trim();
  const selectedToolName = String(form.selectedToolName ?? "").trim();
  const stepName = String(form.stepName ?? "").trim();
  return {
    ...(includeId && id ? { id } : {}),
    visibility: form.visibility,
    name: form.name.trim(),
    description: form.description.trim(),
    instructions: form.agentType === "workflow" ? "" : form.instructions.trim(),
    runtime_prompts: {
      retrieval_context: form.retrievalContext.trim(),
    },
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: [],
    mcp_server_refs: selectedMcpServerSlug ? [selectedMcpServerSlug] : [],
    agent_domain: form.agentDomain.trim() || "default",
    agent_type: form.agentType,
    channel_type: form.channelType,
    interface_type: form.interfaceType,
    workflow_definition: {
      steps: selectedMcpServerSlug && selectedToolName
        ? [{
          id: "step_1",
          name: stepName || selectedToolName,
          mcp_server_slug: selectedMcpServerSlug,
          exposed_tool_name: selectedToolName,
          arguments: parseJsonObject(form.stepArgumentsText, invalidWorkflowMessage),
        }]
        : [],
    },
    tool_policy: parseJsonObject(form.toolPolicyText, invalidToolPolicyMessage),
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
  };
}

export function buildAgentProjectPreview(projectId: string, form: AgentProjectFormState): AgentProjectPreview {
  const defaultModelRef = String(form.defaultModelRef ?? "").trim();
  const selectedMcpServerSlug = String(form.selectedMcpServerSlug ?? "").trim();
  const selectedToolName = String(form.selectedToolName ?? "").trim();
  const stepName = String(form.stepName ?? "").trim();
  const agentDomain = String(form.agentDomain ?? "").trim();
  let stepArguments: Record<string, unknown> = {};
  try {
    stepArguments = parseJsonObject(form.stepArgumentsText, "Invalid workflow definition");
  } catch {
    stepArguments = {};
  }

  return {
    assistant_ref: `agent.project.${projectId || "draft"}`,
    playground_kind: "chat",
    default_model_ref: defaultModelRef || null,
    tool_refs: [],
    mcp_server_refs: selectedMcpServerSlug ? [selectedMcpServerSlug] : [],
    agent_domain: agentDomain || "default",
    agent_type: form.agentType,
    channel_type: form.channelType,
    interface_type: form.interfaceType,
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
    workflow_definition: {
      steps: selectedMcpServerSlug && selectedToolName
        ? [{
          id: "step_1",
          name: stepName || selectedToolName,
          mcp_server_slug: selectedMcpServerSlug,
          exposed_tool_name: selectedToolName,
          arguments: stepArguments,
        }]
        : [],
    },
  };
}
