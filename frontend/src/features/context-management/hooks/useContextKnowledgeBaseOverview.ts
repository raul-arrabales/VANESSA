import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  deleteKnowledgeBase,
  resyncKnowledgeBase,
  updateKnowledgeBase,
} from "../../../api/context";
import { withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import {
  createChunkingFormStateFromKnowledgeBase,
  createDefaultChunkingFormState,
  validateChunkingFormState,
} from "../chunkingForm";
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
    chunking: createDefaultChunkingFormState(),
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
      chunking: createChunkingFormStateFromKnowledgeBase(workspace.knowledgeBase),
    });
  }, [workspace.knowledgeBase]);

  async function handleSaveKnowledgeBase(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    const canEditChunking = workspace.knowledgeBase.document_count === 0;
    const chunkingValidation = validateChunkingFormState({
      form: form.chunking,
      selectedVectorizationMode: workspace.knowledgeBase.vectorization.mode === "self_provided" ? "self_provided" : "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: null,
    });
    if (canEditChunking && !chunkingValidation.ok) {
      workspace.showErrorFeedback(
        t(chunkingValidation.error.key, chunkingValidation.error.values),
        t("contextManagement.feedback.updateFailed"),
      );
      return;
    }
    const normalizedChunking = chunkingValidation.ok ? chunkingValidation.normalizedChunking : null;
    try {
      const updated = await updateKnowledgeBase(
        workspace.knowledgeBase.id,
        {
          slug: form.slug,
          display_name: form.displayName,
          description: form.description,
          lifecycle_state: form.lifecycleState,
          ...(canEditChunking && normalizedChunking
            ? {
                chunking: normalizedChunking,
              }
            : {}),
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
