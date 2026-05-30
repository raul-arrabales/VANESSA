import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import {
  createAgentProject,
  listAgentProjects,
  publishAgentProject,
  updateAgentProject,
  validateAgentProject,
  type AgentProject,
  type AgentProjectPublishResult,
  type AgentProjectValidation,
} from "../../../api/agentProjects";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import {
  buildAgentProjectForm,
  buildGuidedUserAgentCreateForm,
  toAgentProjectMutationInput,
  type AgentProjectFormState,
} from "../../agent-builder/types";

type UseUserAgentProjectsControlResult = {
  projects: AgentProject[];
  loading: boolean;
  saving: boolean;
  validatingProjectId: string;
  publishingProjectId: string;
  selectedProjectId: string | null;
  form: AgentProjectFormState;
  setForm: Dispatch<SetStateAction<AgentProjectFormState>>;
  validations: Record<string, AgentProjectValidation>;
  publishResults: Record<string, AgentProjectPublishResult>;
  selectProject: (project: AgentProject | null) => void;
  setCreateAgentType: (agentType: AgentProjectFormState["agentType"]) => void;
  resetForm: () => void;
  submitForm: () => Promise<AgentProject | null>;
  validateProject: (projectId: string) => Promise<void>;
  publishProject: (projectId: string) => Promise<void>;
  refresh: () => Promise<void>;
};

export function useUserAgentProjectsControl(token: string, existingAgentNames: string[] = []): UseUserAgentProjectsControlResult {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [projects, setProjects] = useState<AgentProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validatingProjectId, setValidatingProjectId] = useState("");
  const [publishingProjectId, setPublishingProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [form, setForm] = useState<AgentProjectFormState>(() => buildGuidedUserAgentCreateForm(null, { existingAgentNames }));
  const [validations, setValidations] = useState<Record<string, AgentProjectValidation>>({});
  const [publishResults, setPublishResults] = useState<Record<string, AgentProjectPublishResult>>({});

  const buildCreateDefaults = (
    projectList: AgentProject[],
    agentType: AgentProjectFormState["agentType"] = "",
  ): AgentProjectFormState => buildGuidedUserAgentCreateForm(null, {
    existingProjectIds: projectList.map((project) => project.id),
    existingAgentNames: [...existingAgentNames, ...projectList.map((project) => project.spec.name)],
    agentType,
  });

  const refresh = async (): Promise<void> => {
    if (!token) {
      setProjects([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const listed = await listAgentProjects(token);
      setProjects(listed);
      setForm((current) => {
        if (selectedProjectId) {
          return current;
        }
        if (
          current.agentType
          || current.id.trim()
          || current.name.trim()
          || current.description.trim()
          || current.workflowActions.length > 0
        ) {
          return current;
        }
        return buildCreateDefaults(listed);
      });
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.agents.userProjects.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [token]);

  const selectProject = (project: AgentProject | null): void => {
    if (!project) {
      setSelectedProjectId(null);
      setForm(buildCreateDefaults(projects));
      return;
    }
    setSelectedProjectId(project.id);
    setForm(buildAgentProjectForm(project));
  };

  const resetForm = (): void => {
    setSelectedProjectId(null);
    setForm(buildCreateDefaults(projects));
  };

  const setCreateAgentType = (agentType: AgentProjectFormState["agentType"]): void => {
    if (selectedProjectId) {
      setForm((current) => ({
        ...current,
        agentType,
        channelType: agentType === "workflow" ? "vanessa_webapp" : "",
        interfaceType: agentType === "workflow" ? "chat" : "",
      }));
      return;
    }
    setForm(buildCreateDefaults(projects, agentType));
  };

  const submitForm = async (): Promise<AgentProject | null> => {
    if (!token) {
      return null;
    }
    setSaving(true);
    try {
      const payload = toAgentProjectMutationInput(form, {
        includeId: !selectedProjectId,
        invalidWorkflowMessage: t("catalogControl.agents.userProjects.invalidWorkflowDefinition"),
        invalidToolPolicyMessage: t("catalogControl.agents.userProjects.invalidToolPolicy"),
      });
      const saved = selectedProjectId
        ? await updateAgentProject(selectedProjectId, payload, token)
        : await createAgentProject(payload, token);
      setProjects((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
      setSelectedProjectId(saved.id);
      setForm(buildAgentProjectForm(saved));
      showSuccessFeedback(
        selectedProjectId
          ? t("catalogControl.agents.userProjects.updated", { name: saved.spec.name })
          : t("catalogControl.agents.userProjects.created", { name: saved.spec.name }),
      );
      return saved;
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.agents.userProjects.saveFailed"));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const validateProject = async (projectId: string): Promise<void> => {
    if (!token) {
      return;
    }
    setValidatingProjectId(projectId);
    try {
      const payload = await validateAgentProject(projectId, token);
      setValidations((current) => ({ ...current, [projectId]: payload }));
      showSuccessFeedback(t("catalogControl.agents.userProjects.validated", { name: payload.agent_project.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.agents.userProjects.validateFailed"));
    } finally {
      setValidatingProjectId("");
    }
  };

  const publishProject = async (projectId: string): Promise<void> => {
    if (!token) {
      return;
    }
    setPublishingProjectId(projectId);
    try {
      const payload = await publishAgentProject(projectId, token);
      setPublishResults((current) => ({ ...current, [projectId]: payload }));
      setProjects((current) => [payload.agent_project, ...current.filter((item) => item.id !== projectId)]);
      if (selectedProjectId === projectId) {
        setForm(buildAgentProjectForm(payload.agent_project));
      }
      showSuccessFeedback(t("catalogControl.agents.userProjects.published", { name: payload.agent_project.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.agents.userProjects.publishFailed"));
    } finally {
      setPublishingProjectId("");
    }
  };

  return {
    projects,
    loading,
    saving,
    validatingProjectId,
    publishingProjectId,
    selectedProjectId,
    form,
    setForm,
    validations,
    publishResults,
    selectProject,
    setCreateAgentType,
    resetForm,
    submitForm,
    validateProject,
    publishProject,
    refresh,
  };
}
