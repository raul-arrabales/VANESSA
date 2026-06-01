import { describe, expect, it } from "vitest";
import type { PreviewableAssistantExperience } from "./assistantExperience";
import { buildAgentProjectPreview, DEFAULT_AGENT_PROJECT_FORM } from "../catalog-admin/userAgentProjectForm";

describe("assistant experience contract", () => {
  it("keeps user-agent preview aligned with the shared snake_case assistant experience shape", () => {
    const preview: PreviewableAssistantExperience = buildAgentProjectPreview("proj-1", {
      ...DEFAULT_AGENT_PROJECT_FORM,
      defaultModelRef: "safe-small",
      toolRefsText: "tool.web_search, tool.files",
    });

    expect(preview).toEqual({
      assistant_ref: "agent.project.proj-1",
      playground_kind: "chat",
      default_model_ref: "safe-small",
      tool_refs: [],
      mcp_server_refs: [],
      agent_domain: "default",
      agent_type: "workflow",
      channel_type: "vanessa_webapp",
      interface_type: "chat",
      runtime_constraints: {
        internet_required: false,
        sandbox_required: false,
      },
      workflow_definition: {
        version: 2,
        actions: [],
      },
    });
    expect("assistantRef" in preview).toBe(false);
    expect("defaultModelRef" in preview).toBe(false);
  });
});
