import { requestJson } from "./modelops/request";

export type CatalogAgentSpec = {
  name: string;
  description: string;
  instructions: string;
  default_model_ref: string | null;
  tool_refs: string[];
  runtime_constraints: {
    internet_required: boolean;
    sandbox_required: boolean;
  };
};

export type CatalogToolSpec = {
  name: string;
  description: string;
  transport: "mcp" | "sandbox_http";
  connection_profile_ref: "default";
  tool_name: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  safety_policy: Record<string, unknown>;
  offline_compatible: boolean;
};

type CatalogEntityMeta = {
  id: string;
  type: "agent" | "tool";
  owner_user_id: number | null;
  visibility: "private" | "unlisted" | "public";
};

export type CatalogAgent = {
  id: string;
  entity: CatalogEntityMeta;
  agent_kind?: "platform" | "user";
  is_platform_agent?: boolean;
  current_version: string;
  status: string;
  published: boolean;
  published_at: string | null;
  spec: CatalogAgentSpec;
};

export type CatalogTool = {
  id: string;
  entity: CatalogEntityMeta;
  current_version: string;
  status: string;
  published: boolean;
  published_at: string | null;
  spec: CatalogToolSpec;
};

export type CatalogAgentMutationInput = {
  id?: string;
  visibility?: "private" | "unlisted" | "public";
  publish: boolean;
} & CatalogAgentSpec;

export type CatalogToolMutationInput = {
  id?: string;
  visibility?: "private" | "unlisted" | "public";
  publish: boolean;
} & CatalogToolSpec;

export type CatalogAgentValidation = {
  agent: CatalogAgent;
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

export type CatalogToolValidation = {
  tool: CatalogTool;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
    runtime_checks: Record<string, unknown>;
  };
};

export type CatalogToolTestResult = {
  tool: CatalogTool;
  execution: {
    input: Record<string, unknown>;
    request_metadata: Record<string, unknown>;
    status_code: number;
    ok: boolean;
    result: Record<string, unknown> | null;
  };
};

export async function listCatalogAgents(token: string): Promise<CatalogAgent[]> {
  const result = await requestJson<{ agents: CatalogAgent[] }>("/v1/catalog/agents", { token });
  return result.agents;
}

export async function createCatalogAgent(input: CatalogAgentMutationInput, token: string): Promise<CatalogAgent> {
  const result = await requestJson<{ agent: CatalogAgent }>("/v1/catalog/agents", {
    method: "POST",
    token,
    body: input,
  });
  return result.agent;
}

export async function updateCatalogAgent(agentId: string, input: CatalogAgentMutationInput, token: string): Promise<CatalogAgent> {
  const result = await requestJson<{ agent: CatalogAgent }>(`/v1/catalog/agents/${encodeURIComponent(agentId)}`, {
    method: "PUT",
    token,
    body: input,
  });
  return result.agent;
}

export async function deleteCatalogAgent(agentId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/catalog/agents/${encodeURIComponent(agentId)}`, {
    method: "DELETE",
    token,
  });
}

export async function validateCatalogAgent(agentId: string, token: string): Promise<CatalogAgentValidation> {
  return requestJson<CatalogAgentValidation>(`/v1/catalog/agents/${encodeURIComponent(agentId)}/validate`, {
    method: "POST",
    token,
  });
}

export async function listCatalogTools(token: string): Promise<CatalogTool[]> {
  const result = await requestJson<{ tools: CatalogTool[] }>("/v1/catalog/tools", { token });
  return result.tools;
}

export async function createCatalogTool(input: CatalogToolMutationInput, token: string): Promise<CatalogTool> {
  const result = await requestJson<{ tool: CatalogTool }>("/v1/catalog/tools", {
    method: "POST",
    token,
    body: input,
  });
  return result.tool;
}

export async function updateCatalogTool(toolId: string, input: CatalogToolMutationInput, token: string): Promise<CatalogTool> {
  const result = await requestJson<{ tool: CatalogTool }>(`/v1/catalog/tools/${encodeURIComponent(toolId)}`, {
    method: "PUT",
    token,
    body: input,
  });
  return result.tool;
}

export async function validateCatalogTool(toolId: string, token: string): Promise<CatalogToolValidation> {
  return requestJson<CatalogToolValidation>(`/v1/catalog/tools/${encodeURIComponent(toolId)}/validate`, {
    method: "POST",
    token,
  });
}

export async function testCatalogTool(
  toolId: string,
  input: Record<string, unknown>,
  token: string,
): Promise<CatalogToolTestResult> {
  return requestJson<CatalogToolTestResult>(`/v1/catalog/tools/${encodeURIComponent(toolId)}/test`, {
    method: "POST",
    token,
    body: { input },
  });
}
