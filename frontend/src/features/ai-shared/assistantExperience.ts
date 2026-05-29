import type { PlaygroundKind } from "../../api/playgrounds";

export type PreviewableAssistantExperience = {
  assistant_ref: string;
  playground_kind: PlaygroundKind;
  default_model_ref: string | null;
  tool_refs: string[];
  mcp_server_refs?: string[];
  agent_domain?: string;
  agent_type?: "workflow" | "planner" | "react";
  channel_type?: "vanessa_webapp";
  interface_type?: "chat";
  runtime_constraints: {
    internet_required: boolean;
    sandbox_required: boolean;
  };
  workflow_definition: Record<string, unknown>;
};
