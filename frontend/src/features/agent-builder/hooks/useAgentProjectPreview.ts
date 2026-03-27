import { useMemo } from "react";
import type { PreviewableAssistantExperience } from "../../ai-shared/assistantExperience";
import { buildAgentProjectPreview, type AgentProjectFormState } from "../types";

export function useAgentProjectPreview(projectId: string, form: AgentProjectFormState): PreviewableAssistantExperience {
  return useMemo(() => buildAgentProjectPreview(projectId, form), [form, projectId]);
}
