import type { PlaygroundKind } from "../../api/playgrounds";

export type PreviewableAssistantExperience = {
  assistant_ref: string;
  playground_kind: PlaygroundKind;
  default_model_ref: string | null;
  tool_refs: string[];
  runtime_constraints: {
    internet_required: boolean;
    sandbox_required: boolean;
  };
  workflow_definition: Record<string, unknown>;
};
