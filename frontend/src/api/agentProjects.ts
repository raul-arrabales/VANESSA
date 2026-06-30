import { ApiError } from "../auth/authApi";
import { readStoredToken } from "../auth/storage";
import { requestJson } from "./modelops/request";

export type AgentProjectVisibility = "private" | "unlisted" | "public";
export type WorkflowVariableType = "text";
export const SUPPORTED_WORKFLOW_VARIABLE_TYPES: WorkflowVariableType[] = ["text"];

export function isSupportedWorkflowVariableType(value: unknown): value is WorkflowVariableType {
  return SUPPORTED_WORKFLOW_VARIABLE_TYPES.includes(value as WorkflowVariableType);
}

export type WorkflowVariableDefinition = {
  name: string;
  label: string;
  type: WorkflowVariableType;
  required?: boolean;
  guidance?: string;
};

export type WorkflowVariableReference = {
  variable: string;
};

export type WorkflowGetUserInputAction = {
  id: string;
  type: "get_user_input";
  name: string;
  prompt: string;
  variables: WorkflowVariableDefinition[];
};

export type WorkflowMcpToolAction = {
  id: string;
  type: "mcp_tool";
  name: string;
  mcp_server_slug: string;
  exposed_tool_name: string;
  prompt: string;
  input_bindings: Record<string, WorkflowVariableReference>;
  output_variables: Array<WorkflowVariableDefinition & { path?: string }>;
};

export type WorkflowSendOutputAction = {
  id: string;
  type: "send_output";
  name: string;
  prompt: string;
  variable_refs: string[];
};

export type WorkflowAction = WorkflowGetUserInputAction | WorkflowMcpToolAction | WorkflowSendOutputAction;

export type WorkflowDefinition = {
  version: number;
  actions: WorkflowAction[];
};

export type WorkflowExecutionMode = "one_time" | "loop";

export type AgentProjectSpec = {
  name: string;
  description: string;
  instructions: string;
  runtime_prompts: {
    retrieval_context?: string;
  };
  default_model_ref: string | null;
  tool_refs: string[];
  mcp_server_refs?: string[];
  agent_domain?: string;
  agent_type: "workflow" | "planner" | "react";
  channel_type: "vanessa_webapp";
  interface_type: "chat";
  workflow_execution_mode?: WorkflowExecutionMode;
  workflow_definition: WorkflowDefinition;
  tool_policy: Record<string, unknown>;
  runtime_constraints: {
    internet_required: boolean;
    sandbox_required: boolean;
  };
};

export type AgentProject = {
  id: string;
  owner_user_id: number;
  published_agent_id: string | null;
  current_version: number;
  visibility: AgentProjectVisibility;
  created_at: string;
  updated_at: string;
  spec: AgentProjectSpec;
};

export type AgentProjectMutationInput = Omit<AgentProjectSpec, "runtime_prompts"> & {
  id?: string;
  visibility?: AgentProjectVisibility;
  runtime_prompts?: {
    retrieval_context?: string;
  };
};

export type AgentProjectValidation = {
  agent_project: AgentProject;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
    resolved_tools: Array<{
      id: string;
      name: string;
      execution_backend: string;
      offline_compatible: boolean;
    }>;
    resolved_mcp_servers?: Array<{
      id: string;
      slug: string;
      name: string;
      backing_tool_id: string;
      enabled: boolean;
    }>;
    derived_runtime_requirements: {
      internet_required: boolean;
      sandbox_required: boolean;
    };
  };
};

export type AgentProjectPublishResult = {
  agent_project: AgentProject;
  publish_result: {
    agent_id: string;
    catalog_agent: Record<string, unknown>;
    published_at: string;
  };
};

export type AgentProjectDefaults = {
  agent: {
    runtime_prompts: {
      retrieval_context: string;
    };
  };
};

function requireToken(token?: string): string {
  const activeToken = token || readStoredToken();
  if (!activeToken) {
    throw new ApiError("Authentication required", 401, "missing_auth");
  }
  return activeToken;
}

export async function listAgentProjects(token?: string): Promise<AgentProject[]> {
  const result = await requestJson<{ agent_projects: AgentProject[] }>("/v1/agent-projects", {
    token: requireToken(token),
  });
  return result.agent_projects;
}

export async function getAgentProjectDefaults(token?: string): Promise<AgentProjectDefaults> {
  const result = await requestJson<{ defaults: AgentProjectDefaults }>("/v1/catalog/defaults", {
    token: requireToken(token),
  });
  return result.defaults;
}

export async function createAgentProject(input: AgentProjectMutationInput, token?: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>("/v1/agent-projects", {
    method: "POST",
    token: requireToken(token),
    body: input,
  });
  return result.agent_project;
}

export async function getAgentProject(projectId: string, token?: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>(
    `/v1/agent-projects/${encodeURIComponent(projectId)}`,
    { token: requireToken(token) },
  );
  return result.agent_project;
}

export async function updateAgentProject(projectId: string, input: AgentProjectMutationInput, token?: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>(`/v1/agent-projects/${encodeURIComponent(projectId)}`, {
    method: "PUT",
    token: requireToken(token),
    body: input,
  });
  return result.agent_project;
}

export async function validateAgentProject(projectId: string, token?: string): Promise<AgentProjectValidation> {
  return requestJson<AgentProjectValidation>(`/v1/agent-projects/${encodeURIComponent(projectId)}/validate`, {
    method: "POST",
    token: requireToken(token),
  });
}

export async function publishAgentProject(projectId: string, token?: string): Promise<AgentProjectPublishResult> {
  return requestJson<AgentProjectPublishResult>(`/v1/agent-projects/${encodeURIComponent(projectId)}/publish`, {
    method: "POST",
    token: requireToken(token),
  });
}

export async function deleteAgentProject(projectId: string, token?: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/agent-projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
    token: requireToken(token),
  });
}
