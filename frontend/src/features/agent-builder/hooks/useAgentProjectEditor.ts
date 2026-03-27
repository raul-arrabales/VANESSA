import { useEffect, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  getAgentProject,
  publishAgentProject,
  updateAgentProject,
  validateAgentProject,
  type AgentProject,
  type AgentProjectPublishResult,
  type AgentProjectValidation,
} from "../../../api/agentProjects";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { buildAgentProjectForm, toAgentProjectMutationInput, type AgentProjectFormState } from "../types";

type UseAgentProjectEditorResult = {
  projectId: string;
  project: AgentProject | null;
  form: AgentProjectFormState;
  setForm: Dispatch<SetStateAction<AgentProjectFormState>>;
  loading: boolean;
  saving: boolean;
  validating: boolean;
  publishing: boolean;
  validation: AgentProjectValidation | null;
  publishResult: AgentProjectPublishResult | null;
  handleSave: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleValidate: () => Promise<void>;
  handlePublish: () => Promise<void>;
  handleBack: () => void;
};

export function useAgentProjectEditor(): UseAgentProjectEditorResult {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId = "" } = useParams<{ projectId: string }>();
  const { token } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [project, setProject] = useState<AgentProject | null>(null);
  const [form, setForm] = useState<AgentProjectFormState>({
    ...DEFAULT_EMPTY_FORM,
    id: projectId,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [validation, setValidation] = useState<AgentProjectValidation | null>(null);
  const [publishResult, setPublishResult] = useState<AgentProjectPublishResult | null>(null);

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (!token || !projectId) {
      setLoading(false);
      return;
    }
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const loadedProject = await getAgentProject(projectId, token);
        setProject(loadedProject);
        setForm(buildAgentProjectForm(loadedProject));
      } catch (error) {
        showErrorFeedback(error, t("agentBuilder.feedback.loadFailed"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [projectId, showErrorFeedback, t, token]);

  async function handleSave(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !projectId) {
      return;
    }
    setSaving(true);
    try {
      const savedProject = await updateAgentProject(
        projectId,
        toAgentProjectMutationInput(form, {
          includeId: false,
          invalidWorkflowMessage: t("agentBuilder.feedback.invalidWorkflowDefinition"),
          invalidToolPolicyMessage: t("agentBuilder.feedback.invalidToolPolicy"),
        }),
        token,
      );
      setProject(savedProject);
      setForm(buildAgentProjectForm(savedProject));
      showSuccessFeedback(t("agentBuilder.feedback.updated", { name: savedProject.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("agentBuilder.feedback.updateFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate(): Promise<void> {
    if (!token || !projectId) {
      return;
    }
    setValidating(true);
    try {
      const payload = await validateAgentProject(projectId, token);
      setValidation(payload);
      showSuccessFeedback(t("agentBuilder.feedback.validated", { name: payload.agent_project.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("agentBuilder.feedback.validateFailed"));
    } finally {
      setValidating(false);
    }
  }

  async function handlePublish(): Promise<void> {
    if (!token || !projectId) {
      return;
    }
    setPublishing(true);
    try {
      const payload = await publishAgentProject(projectId, token);
      setPublishResult(payload);
      setProject(payload.agent_project);
      showSuccessFeedback(t("agentBuilder.feedback.published", { name: payload.agent_project.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("agentBuilder.feedback.publishFailed"));
    } finally {
      setPublishing(false);
    }
  }

  function handleBack(): void {
    navigate("/control/agent-builder");
  }

  return {
    projectId,
    project,
    form,
    setForm,
    loading,
    saving,
    validating,
    publishing,
    validation,
    publishResult,
    handleSave,
    handleValidate,
    handlePublish,
    handleBack,
  };
}

const DEFAULT_EMPTY_FORM: AgentProjectFormState = {
  id: "",
  visibility: "private",
  name: "",
  description: "",
  instructions: "",
  defaultModelRef: "",
  toolRefsText: "",
  workflowDefinitionText: "{\n  \"entrypoint\": \"assistant\"\n}",
  toolPolicyText: "{\n  \"allow_user_tools\": false\n}",
  internetRequired: false,
  sandboxRequired: false,
};
