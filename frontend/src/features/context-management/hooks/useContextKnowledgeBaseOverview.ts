import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  deleteKnowledgeBase,
  resyncKnowledgeBase,
  updateKnowledgeBase,
} from "../../../api/context";
import { withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import type { KnowledgeBaseOverviewFormState } from "../types";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export type ContextKnowledgeBaseOverviewResult = ReturnType<typeof useContextKnowledgeBaseLoader> & {
  form: KnowledgeBaseOverviewFormState;
  setForm: Dispatch<SetStateAction<KnowledgeBaseOverviewFormState>>;
  isResyncing: boolean;
  handleSaveKnowledgeBase: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleDeleteKnowledgeBase: () => Promise<void>;
  handleResyncKnowledgeBase: () => Promise<void>;
};

export function useContextKnowledgeBaseOverview(): ContextKnowledgeBaseOverviewResult {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const workspace = useContextKnowledgeBaseLoader();
  const [form, setForm] = useState<KnowledgeBaseOverviewFormState>({
    slug: "",
    displayName: "",
    description: "",
    lifecycleState: "active",
  });
  const [isResyncing, setIsResyncing] = useState(false);

  useEffect(() => {
    if (!workspace.knowledgeBase) {
      return;
    }
    setForm({
      slug: workspace.knowledgeBase.slug,
      displayName: workspace.knowledgeBase.display_name,
      description: workspace.knowledgeBase.description,
      lifecycleState: workspace.knowledgeBase.lifecycle_state,
    });
  }, [workspace.knowledgeBase]);

  async function handleSaveKnowledgeBase(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    try {
      const updated = await updateKnowledgeBase(
        workspace.knowledgeBase.id,
        {
          slug: form.slug,
          display_name: form.displayName,
          description: form.description,
          lifecycle_state: form.lifecycleState,
        },
        workspace.token,
      );
      workspace.setKnowledgeBase(updated);
      workspace.showSuccessFeedback(t("contextManagement.feedback.updated", { name: updated.display_name }));
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.updateFailed"));
    }
  }

  async function handleDeleteKnowledgeBase(): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeBase(workspace.knowledgeBase.id, workspace.token);
      navigate("/control/context", {
        state: withActionFeedbackState({
          kind: "success",
          message: t("contextManagement.feedback.deleted", { name: workspace.knowledgeBase.display_name }),
        }),
      });
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.deleteFailed"));
    }
  }

  async function handleResyncKnowledgeBase(): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin || isResyncing) {
      return;
    }
    setIsResyncing(true);
    try {
      const refreshed = await resyncKnowledgeBase(workspace.knowledgeBase.id, workspace.token);
      workspace.setKnowledgeBase(refreshed);
      await workspace.reload();
      workspace.showSuccessFeedback(t("contextManagement.feedback.resynced", { name: refreshed.display_name }));
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.resyncFailed"));
    } finally {
      setIsResyncing(false);
    }
  }

  return {
    ...workspace,
    form,
    setForm,
    isResyncing,
    handleSaveKnowledgeBase,
    handleDeleteKnowledgeBase,
    handleResyncKnowledgeBase,
  };
}
