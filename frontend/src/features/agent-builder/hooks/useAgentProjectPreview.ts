import { useMemo } from "react";
import { buildAgentProjectPreview, type AgentProjectFormState, type AgentProjectPreview } from "../types";

export function useAgentProjectPreview(projectId: string, form: AgentProjectFormState): AgentProjectPreview {
  return useMemo(() => buildAgentProjectPreview(projectId, form), [form, projectId]);
}
