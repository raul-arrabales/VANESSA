import type { AgentProjectSpec } from "../../api/agentProjects";
import type { CatalogDefaults } from "../../api/catalog";

export type WorkflowRuntimePrompts = NonNullable<AgentProjectSpec["runtime_prompts"]>;

export function workflowRuntimePromptsFromDefaults(defaults: CatalogDefaults | null): WorkflowRuntimePrompts {
  return {
    retrieval_context: defaults?.agent.runtime_prompts.retrieval_context ?? "",
    workflow_input_extraction: defaults?.agent.runtime_prompts.workflow_input_extraction ?? "",
    workflow_tool_arguments: defaults?.agent.runtime_prompts.workflow_tool_arguments ?? "",
    workflow_output_response: defaults?.agent.runtime_prompts.workflow_output_response ?? "",
  };
}

export function workflowRuntimePromptsFromSpec(
  runtimePrompts: AgentProjectSpec["runtime_prompts"] | undefined,
  defaults: CatalogDefaults | null = null,
): WorkflowRuntimePrompts {
  const defaultPrompts = workflowRuntimePromptsFromDefaults(defaults);
  return {
    retrieval_context: runtimePrompts?.retrieval_context ?? defaultPrompts.retrieval_context,
    workflow_input_extraction: runtimePrompts?.workflow_input_extraction ?? defaultPrompts.workflow_input_extraction,
    workflow_tool_arguments: runtimePrompts?.workflow_tool_arguments ?? defaultPrompts.workflow_tool_arguments,
    workflow_output_response: runtimePrompts?.workflow_output_response ?? defaultPrompts.workflow_output_response,
  };
}
