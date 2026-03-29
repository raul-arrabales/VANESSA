import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "../../auth/types";
import { renderWithAppProviders } from "../../test/renderWithAppProviders";
import AgentBuilderProjectsPage from "./pages/AgentBuilderProjectsPage";
import AgentProjectDetailPage from "./pages/AgentProjectDetailPage";
import * as agentProjectsApi from "../../api/agentProjects";

let mockUser: AuthUser | null = null;

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("../../api/agentProjects", () => ({
  listAgentProjects: vi.fn(),
  createAgentProject: vi.fn(),
  getAgentProject: vi.fn(),
  updateAgentProject: vi.fn(),
  validateAgentProject: vi.fn(),
  publishAgentProject: vi.fn(),
}));

const projectFixture = {
  id: "proj-1",
  owner_user_id: 10,
  published_agent_id: null,
  current_version: 1,
  visibility: "private" as const,
  created_at: "2026-03-18T11:00:00Z",
  updated_at: "2026-03-18T11:00:00Z",
  spec: {
    name: "Support Agent",
    description: "Handles support workflows.",
    instructions: "Be helpful.",
    default_model_ref: "safe-small",
    tool_refs: ["tool.web_search"],
    workflow_definition: { entrypoint: "assistant" },
    tool_policy: { allow_user_tools: false },
    runtime_constraints: { internet_required: true, sandbox_required: false },
  },
};

describe("Agent builder pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 10,
      email: "builder@example.com",
      username: "builder",
      role: "user",
      is_active: true,
    };
    vi.mocked(agentProjectsApi.listAgentProjects).mockResolvedValue([projectFixture]);
    vi.mocked(agentProjectsApi.createAgentProject).mockResolvedValue(projectFixture);
    vi.mocked(agentProjectsApi.getAgentProject).mockResolvedValue(projectFixture);
    vi.mocked(agentProjectsApi.updateAgentProject).mockResolvedValue(projectFixture);
    vi.mocked(agentProjectsApi.validateAgentProject).mockResolvedValue({
      agent_project: projectFixture,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
        resolved_tools: [],
        derived_runtime_requirements: { internet_required: true, sandbox_required: false },
      },
    });
    vi.mocked(agentProjectsApi.publishAgentProject).mockResolvedValue({
      agent_project: { ...projectFixture, published_agent_id: "agent.project.proj-1" },
      publish_result: {
        agent_id: "agent.project.proj-1",
        catalog_agent: { id: "agent.project.proj-1" },
        published_at: "2026-03-18T11:05:00Z",
      },
    });
  });

  it("creates a project from the builder workspace", async () => {
    const user = userEvent.setup();
    vi.mocked(agentProjectsApi.listAgentProjects).mockResolvedValue([]);

    await renderWithAppProviders(<AgentBuilderProjectsPage />, { route: "/agent-builder" });

    await user.type(screen.getByLabelText("Project ID"), "proj-1");
    await user.type(screen.getByLabelText("Name"), "Support Agent");
    await user.type(screen.getByLabelText("Description"), "Handles support workflows.");
    await user.type(screen.getByLabelText("Instructions"), "Be helpful.");
    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() => {
      expect(agentProjectsApi.createAgentProject).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "proj-1",
          name: "Support Agent",
        }),
        "token",
      );
    });
  });

  it("publishes a project from the detail workspace", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(
      <Routes>
        <Route path="/agent-builder/:projectId" element={<AgentProjectDetailPage />} />
      </Routes>,
      { route: "/agent-builder/proj-1" },
    );

    await user.click(await screen.findByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(agentProjectsApi.publishAgentProject).toHaveBeenCalledWith("proj-1", "token");
    });
    expect(await screen.findByText("agent.project.proj-1")).toBeVisible();
  });
});
