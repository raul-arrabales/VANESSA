import type { AgentProjectSpec } from "../../api/agentProjects";
import type { CatalogDefaults } from "../../api/catalog";

export type WorkflowRuntimePrompts = NonNullable<AgentProjectSpec["runtime_prompts"]>;

export function workflowRuntimePromptsFromDefaults(defaults: CatalogDefaults | null): WorkflowRuntimePrompts {
  return {
    retrieval_context: defaults?.agent.runtime_prompts.retrieval_context ?? "",
  };
}

export function workflowRuntimePromptsFromSpec(
  runtimePrompts: AgentProjectSpec["runtime_prompts"] | undefined,
  defaults: CatalogDefaults | null = null,
): WorkflowRuntimePrompts {
  const defaultPrompts = workflowRuntimePromptsFromDefaults(defaults);
  return {
    retrieval_context: runtimePrompts?.retrieval_context ?? defaultPrompts.retrieval_context,
  };
}
