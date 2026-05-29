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

export function buildDefaultAgentProjectForm(defaults: CatalogDefaults | null): AgentProjectFormState {
  return {
    id: "",
    visibility: "private",
    name: "",
    description: "",
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
    selectedMcpServerSlug: project.spec.workflow_definition.steps[0]?.mcp_server_slug ?? "",
    selectedToolName: project.spec.workflow_definition.steps[0]?.exposed_tool_name ?? "",
    stepName: project.spec.workflow_definition.steps[0]?.name ?? "",
    stepArgumentsText: JSON.stringify(project.spec.workflow_definition.steps[0]?.arguments ?? {}, null, 2),
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
  return {
    ...(includeId && id ? { id } : {}),
    visibility: form.visibility,
    name: form.name.trim(),
    description: form.description.trim(),
    instructions: form.instructions.trim(),
    runtime_prompts: {
      retrieval_context: form.retrievalContext.trim(),
    },
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: [],
    mcp_server_refs: form.selectedMcpServerSlug.trim() ? [form.selectedMcpServerSlug.trim()] : [],
    agent_domain: form.agentDomain.trim() || "default",
    agent_type: form.agentType,
    channel_type: form.channelType,
    interface_type: form.interfaceType,
    workflow_definition: {
      steps: form.selectedMcpServerSlug.trim() && form.selectedToolName.trim()
        ? [{
          id: "step_1",
          name: form.stepName.trim() || form.selectedToolName.trim(),
          mcp_server_slug: form.selectedMcpServerSlug.trim(),
          exposed_tool_name: form.selectedToolName.trim(),
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
  let stepArguments: Record<string, unknown> = {};
  try {
    stepArguments = parseJsonObject(form.stepArgumentsText, "Invalid workflow definition");
  } catch {
    stepArguments = {};
  }

  return {
    assistant_ref: `agent.project.${projectId || "draft"}`,
    playground_kind: "chat",
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: [],
    mcp_server_refs: form.selectedMcpServerSlug.trim() ? [form.selectedMcpServerSlug.trim()] : [],
    agent_domain: form.agentDomain.trim() || "default",
    agent_type: form.agentType,
    channel_type: form.channelType,
    interface_type: form.interfaceType,
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
    workflow_definition: {
      steps: form.selectedMcpServerSlug.trim() && form.selectedToolName.trim()
        ? [{
          id: "step_1",
          name: form.stepName.trim() || form.selectedToolName.trim(),
          mcp_server_slug: form.selectedMcpServerSlug.trim(),
          exposed_tool_name: form.selectedToolName.trim(),
          arguments: stepArguments,
        }]
        : [],
    },
  };
}
