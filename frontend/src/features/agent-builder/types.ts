import type { AgentProject, AgentProjectMutationInput, AgentProjectVisibility } from "../../api/agentProjects";
import type { PreviewableAssistantExperience } from "../ai-shared/assistantExperience";

export type AgentProjectFormState = {
  id: string;
  visibility: AgentProjectVisibility;
  name: string;
  description: string;
  instructions: string;
  defaultModelRef: string;
  toolRefsText: string;
  workflowDefinitionText: string;
  toolPolicyText: string;
  internetRequired: boolean;
  sandboxRequired: boolean;
};

export type AgentProjectPreview = PreviewableAssistantExperience;

export const DEFAULT_AGENT_PROJECT_FORM: AgentProjectFormState = {
  id: "",
  visibility: "private",
  name: "",
  description: "",
  instructions: "",
  defaultModelRef: "",
  toolRefsText: "",
  workflowDefinitionText: "{\n  \"entrypoint\": \"assistant\"\n}",
  toolPolicyText: "{\n  \"allow_user_tools\": false\n}",
  internetRequired: false,
  sandboxRequired: false,
};

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
    defaultModelRef: project.spec.default_model_ref ?? "",
    toolRefsText: project.spec.tool_refs.join(", "),
    workflowDefinitionText: JSON.stringify(project.spec.workflow_definition, null, 2),
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
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: form.toolRefsText
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean),
    workflow_definition: parseJsonObject(form.workflowDefinitionText, invalidWorkflowMessage),
    tool_policy: parseJsonObject(form.toolPolicyText, invalidToolPolicyMessage),
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
  };
}

export function buildAgentProjectPreview(projectId: string, form: AgentProjectFormState): AgentProjectPreview {
  let workflowDefinition: Record<string, unknown> = {};
  try {
    workflowDefinition = parseJsonObject(form.workflowDefinitionText, "Invalid workflow definition");
  } catch {
    workflowDefinition = {};
  }

  return {
    assistant_ref: `agent.project.${projectId || "draft"}`,
    playground_kind: "chat",
    default_model_ref: form.defaultModelRef.trim() || null,
    tool_refs: form.toolRefsText
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean),
    runtime_constraints: {
      internet_required: form.internetRequired,
      sandbox_required: form.sandboxRequired,
    },
    workflow_definition: workflowDefinition,
  };
}
