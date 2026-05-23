import { requestJson } from "./modelops/request";

export type CatalogAgentSpec = {
  name: string;
  description: string;
  instructions: string;
  runtime_prompts: {
    retrieval_context: string;
  };
  default_model_ref: string | null;
  tool_refs: string[];
  mcp_server_refs?: string[];
  agent_domain?: string;
  runtime_constraints: {
    internet_required: boolean;
    sandbox_required: boolean;
  };
};

export type CatalogDefaults = {
  agent: {
    runtime_prompts: {
      retrieval_context: string;
    };
  };
};

export type CatalogToolSpec = {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  safety_policy: Record<string, unknown>;
  offline_compatible: boolean;
  execution_backend?: "sandbox_python" | "mcp_gateway_web_search" | "internal_http" | "knowledge_base_retrieval" | "image_analysis" | "image_generation";
  execution_config?: Record<string, unknown>;
  permissions?: Record<string, unknown>;
};

export type CatalogToolExecutionBackend = NonNullable<CatalogToolSpec["execution_backend"]>;

export type CatalogKnowledgeBaseOption = {
  id: string;
  display_name: string;
  slug?: string | null;
  index_name?: string | null;
  is_default?: boolean;
};

export type CatalogToolCreationBackendOption =
  | {
      execution_backend: Exclude<CatalogToolExecutionBackend, "knowledge_base_retrieval">;
      requires_knowledge_base: false;
      template: CatalogToolMutationInput;
    }
  | {
      execution_backend: "knowledge_base_retrieval";
      requires_knowledge_base: true;
      knowledge_bases: CatalogKnowledgeBaseOption[];
      templates_by_knowledge_base_id: Record<string, CatalogToolMutationInput>;
    };

export type CatalogToolCreationOptions = {
  execution_backends: CatalogToolCreationBackendOption[];
  knowledge_bases: CatalogKnowledgeBaseOption[];
  default_knowledge_base_id?: string | null;
  selection_required: boolean;
  configuration_message?: string | null;
};

export type CatalogValidationStatus = {
  last_validation_status: string;
  is_validation_current: boolean;
  validated_version: string | null;
  last_validated_at: string | null;
  validation_errors: string[];
};

export type CatalogMcpServerSpec = {
  name: string;
  slug: string;
  description: string;
  backing_tool_id: string;
  exposed_tool_name: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  metadata: {
    category: "web_search" | "knowledge_retrieval" | "code_execution" | "data_analysis" | "creative_media" | "automation" | "communication" | "custom";
    capabilities: string[];
    local: boolean;
    stateless: boolean;
    sandboxed: boolean;
    risk_level: "low" | "medium" | "high";
    data_access: "none" | "public_web" | "workspace" | "user_data" | "secrets_or_credentials";
    output_freshness: "static" | "fresh" | "runtime_generated";
    audit_level: "standard" | "elevated";
  };
  authorization_policy: {
    agent_ids: string[];
    agent_domains: string[];
    agent_roles: string[];
    user_roles: string[];
    user_ids: string[];
    user_group_ids: string[];
  };
  enabled: boolean;
};

export type CatalogMcpCreationOptions = {
  tools: Array<{
    tool_id: string;
    metadata_defaults: CatalogMcpServerSpec["metadata"];
  }>;
};

type CatalogEntityMeta = {
  id: string;
  type: "agent" | "tool" | "mcp_server";
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
  created_at?: string | null;
  updated_at?: string | null;
  spec: CatalogAgentSpec;
};

export type CatalogTool = {
  id: string;
  entity: CatalogEntityMeta;
  current_version: string;
  status: string;
  published: boolean;
  published_at: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  spec: CatalogToolSpec;
  validation_status?: CatalogValidationStatus;
};

export type CatalogMcpServer = {
  id: string;
  entity: CatalogEntityMeta;
  current_version: string;
  status: string;
  published: boolean;
  published_at: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  spec: CatalogMcpServerSpec;
  validation_status: CatalogValidationStatus;
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

export type CatalogMcpServerMutationInput = {
  id?: string;
  visibility?: "private" | "unlisted" | "public";
  publish: boolean;
} & CatalogMcpServerSpec;

export type CatalogAgentValidation = {
  agent: CatalogAgent;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
    resolved_tools: Array<{
      id: string;
      name: string;
      execution_backend?: string;
      offline_compatible: boolean;
    }>;
    resolved_mcp_servers?: Array<{
      id: string;
      slug: string;
      name: string;
      backing_tool_id: string;
      enabled: boolean;
      metadata?: CatalogMcpServerSpec["metadata"];
    }>;
    derived_runtime_requirements: {
      internet_required: boolean;
      sandbox_required: boolean;
    };
  };
};

export type CatalogAgentPromptPreview = {
  agent?: CatalogAgent;
  prompt_preview: {
    messages: Array<{
      role: "system";
      label: string;
      content: string;
    }>;
    text: string;
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

export type CatalogMcpServerValidation = {
  mcp_server: CatalogMcpServer;
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

export async function getCatalogDefaults(token: string): Promise<CatalogDefaults> {
  const result = await requestJson<{ defaults: CatalogDefaults }>("/v1/catalog/defaults", { token });
  return result.defaults;
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

export async function previewCatalogAgentPrompt(input: CatalogAgentMutationInput, token: string): Promise<CatalogAgentPromptPreview> {
  return requestJson<CatalogAgentPromptPreview>("/v1/catalog/agents/prompt-preview", {
    method: "POST",
    token,
    body: input,
  });
}

export async function getCatalogAgentPromptPreview(agentId: string, token: string): Promise<CatalogAgentPromptPreview> {
  return requestJson<CatalogAgentPromptPreview>(`/v1/catalog/agents/${encodeURIComponent(agentId)}/prompt-preview`, {
    token,
  });
}

export async function listCatalogTools(token: string): Promise<CatalogTool[]> {
  const result = await requestJson<{ tools: CatalogTool[] }>("/v1/catalog/tools", { token });
  return result.tools;
}

export async function getCatalogToolCreationOptions(token: string): Promise<CatalogToolCreationOptions> {
  return requestJson<CatalogToolCreationOptions>("/v1/catalog/tool-creation-options", { token });
}

export async function getCatalogMcpCreationOptions(token: string): Promise<CatalogMcpCreationOptions> {
  return requestJson<CatalogMcpCreationOptions>("/v1/catalog/mcp-creation-options", { token });
}

export async function listCatalogMcpServers(token: string): Promise<CatalogMcpServer[]> {
  const result = await requestJson<{ mcp_servers: CatalogMcpServer[] }>("/v1/catalog/mcp-servers", { token });
  return result.mcp_servers;
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

export async function createCatalogMcpServer(input: CatalogMcpServerMutationInput, token: string): Promise<CatalogMcpServer> {
  const result = await requestJson<{ mcp_server: CatalogMcpServer }>("/v1/catalog/mcp-servers", {
    method: "POST",
    token,
    body: input,
  });
  return result.mcp_server;
}

export async function updateCatalogMcpServer(mcpServerId: string, input: CatalogMcpServerMutationInput, token: string): Promise<CatalogMcpServer> {
  const result = await requestJson<{ mcp_server: CatalogMcpServer }>(`/v1/catalog/mcp-servers/${encodeURIComponent(mcpServerId)}`, {
    method: "PUT",
    token,
    body: input,
  });
  return result.mcp_server;
}

export async function deleteCatalogMcpServer(mcpServerId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/catalog/mcp-servers/${encodeURIComponent(mcpServerId)}`, {
    method: "DELETE",
    token,
  });
}

export async function validateCatalogTool(toolId: string, token: string): Promise<CatalogToolValidation> {
  return requestJson<CatalogToolValidation>(`/v1/catalog/tools/${encodeURIComponent(toolId)}/validate`, {
    method: "POST",
    token,
  });
}

export async function validateCatalogMcpServer(mcpServerId: string, token: string): Promise<CatalogMcpServerValidation> {
  return requestJson<CatalogMcpServerValidation>(`/v1/catalog/mcp-servers/${encodeURIComponent(mcpServerId)}/validate`, {
    method: "POST",
    token,
  });
}

export async function setCatalogMcpServerEnabled(mcpServerId: string, enabled: boolean, token: string): Promise<CatalogMcpServer> {
  const result = await requestJson<{ mcp_server: CatalogMcpServer }>(
    `/v1/catalog/mcp-servers/${encodeURIComponent(mcpServerId)}/${enabled ? "enable" : "disable"}`,
    {
      method: "POST",
      token,
    },
  );
  return result.mcp_server;
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
