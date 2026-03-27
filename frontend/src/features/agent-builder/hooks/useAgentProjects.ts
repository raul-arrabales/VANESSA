import { useEffect, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { createAgentProject, listAgentProjects, type AgentProject } from "../../../api/agentProjects";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, useRouteActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { DEFAULT_AGENT_PROJECT_FORM, toAgentProjectMutationInput, type AgentProjectFormState } from "../types";

type UseAgentProjectsResult = {
  projects: AgentProject[];
  loading: boolean;
  creating: boolean;
  errorMessage: string;
  form: AgentProjectFormState;
  setForm: Dispatch<SetStateAction<AgentProjectFormState>>;
  handleCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function useAgentProjects(): UseAgentProjectsResult {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = useAuth();
  const { showErrorFeedback } = useActionFeedback();
  const [projects, setProjects] = useState<AgentProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [form, setForm] = useState<AgentProjectFormState>(DEFAULT_AGENT_PROJECT_FORM);

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    const load = async (): Promise<void> => {
      setLoading(true);
      setErrorMessage("");
      try {
        setProjects(await listAgentProjects(token));
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : t("agentBuilder.feedback.loadFailed"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [t, token]);

  async function handleCreate(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    setCreating(true);
    try {
      const project = await createAgentProject(
        toAgentProjectMutationInput(form, {
          includeId: true,
          invalidWorkflowMessage: t("agentBuilder.feedback.invalidWorkflowDefinition"),
          invalidToolPolicyMessage: t("agentBuilder.feedback.invalidToolPolicy"),
        }),
        token,
      );
      navigate(`/control/agent-builder/${project.id}`, {
        state: withActionFeedbackState({
          kind: "success",
          message: t("agentBuilder.feedback.created", { name: project.spec.name }),
        }),
      });
    } catch (error) {
      showErrorFeedback(error, t("agentBuilder.feedback.createFailed"));
    } finally {
      setCreating(false);
    }
  }

  return {
    projects,
    loading,
    creating,
    errorMessage,
    form,
    setForm,
    handleCreate,
  };
}
