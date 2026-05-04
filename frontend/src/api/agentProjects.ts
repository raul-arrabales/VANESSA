import { requestJson } from "./modelops/request";

export type AgentProjectVisibility = "private" | "unlisted" | "public";

export type AgentProjectSpec = {
  name: string;
  description: string;
  instructions: string;
  runtime_prompts: {
    retrieval_context: string;
  };
  default_model_ref: string | null;
  tool_refs: string[];
  workflow_definition: Record<string, unknown>;
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

export type AgentProjectMutationInput = {
  id?: string;
  visibility?: AgentProjectVisibility;
} & AgentProjectSpec;

export type AgentProjectValidation = {
  agent_project: AgentProject;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
    resolved_tools: Array<{
      id: string;
      name: string;
      transport: string;
      offline_compatible: boolean;
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

export async function listAgentProjects(token: string): Promise<AgentProject[]> {
  const result = await requestJson<{ agent_projects: AgentProject[] }>("/v1/agent-projects", { token });
  return result.agent_projects;
}

export async function createAgentProject(input: AgentProjectMutationInput, token: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>("/v1/agent-projects", {
    method: "POST",
    token,
    body: input,
  });
  return result.agent_project;
}

export async function getAgentProject(projectId: string, token: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>(`/v1/agent-projects/${encodeURIComponent(projectId)}`, { token });
  return result.agent_project;
}

export async function updateAgentProject(projectId: string, input: AgentProjectMutationInput, token: string): Promise<AgentProject> {
  const result = await requestJson<{ agent_project: AgentProject }>(`/v1/agent-projects/${encodeURIComponent(projectId)}`, {
    method: "PUT",
    token,
    body: input,
  });
  return result.agent_project;
}

export async function validateAgentProject(projectId: string, token: string): Promise<AgentProjectValidation> {
  return requestJson<AgentProjectValidation>(`/v1/agent-projects/${encodeURIComponent(projectId)}/validate`, {
    method: "POST",
    token,
  });
}

export async function publishAgentProject(projectId: string, token: string): Promise<AgentProjectPublishResult> {
  return requestJson<AgentProjectPublishResult>(`/v1/agent-projects/${encodeURIComponent(projectId)}/publish`, {
    method: "POST",
    token,
  });
}
