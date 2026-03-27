import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createKnowledgeBase } from "../../../api/context";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";

type UseContextKnowledgeBaseCreateResult = {
  slug: string;
  displayName: string;
  description: string;
  schemaText: string;
  saving: boolean;
  setSlug: (value: string) => void;
  setDisplayName: (value: string) => void;
  setDescription: (value: string) => void;
  setSchemaText: (value: string) => void;
  handleSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function useContextKnowledgeBaseCreate(): UseContextKnowledgeBaseCreateResult {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showErrorFeedback } = useActionFeedback();
  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [schemaText, setSchemaText] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    let schema: Record<string, unknown> | undefined;
    if (schemaText.trim()) {
      try {
        schema = JSON.parse(schemaText) as Record<string, unknown>;
      } catch {
        showErrorFeedback(t("contextManagement.feedback.invalidSchema"), t("contextManagement.feedback.createFailed"));
        return;
      }
    }
    setSaving(true);
    try {
      const knowledgeBase = await createKnowledgeBase({
        slug,
        display_name: displayName,
        description,
        backing_provider_key: "weaviate_local",
        lifecycle_state: "active",
        schema,
      }, token);
      navigate(`/control/context/${knowledgeBase.id}`, {
        state: withActionFeedbackState({
          kind: "success",
          message: t("contextManagement.feedback.created", { name: knowledgeBase.display_name }),
        }),
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.createFailed"));
    } finally {
      setSaving(false);
    }
  }

  return {
    slug,
    displayName,
    description,
    schemaText,
    saving,
    setSlug,
    setDisplayName,
    setDescription,
    setSchemaText,
    handleSubmit,
  };
}
