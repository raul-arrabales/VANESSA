import type { PreviewableAssistantExperience } from "../ai-shared/assistantExperience";

export const VANESSA_CORE_ASSISTANT_EXPERIENCE: PreviewableAssistantExperience = {
  assistant_ref: "assistant.vanessa.core",
  playground_kind: "chat",
  default_model_ref: null,
  tool_refs: [],
  runtime_constraints: {
    internet_required: false,
    sandbox_required: false,
  },
  workflow_definition: {
    entrypoint: "assistant",
    assistant_variant: "vanessa_core",
  },
};
