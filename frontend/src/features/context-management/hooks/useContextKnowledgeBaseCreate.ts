import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createKnowledgeBase } from "../../../api/context";
import { listPlatformProviders, type PlatformProvider } from "../../../api/platform";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";

type UseContextKnowledgeBaseCreateResult = {
  slug: string;
  displayName: string;
  description: string;
  schemaText: string;
  providerOptions: PlatformProvider[];
  selectedProviderId: string;
  providerLoadError: string;
  providersLoading: boolean;
  saving: boolean;
  setSlug: (value: string) => void;
  setDisplayName: (value: string) => void;
  setDescription: (value: string) => void;
  setSchemaText: (value: string) => void;
  setSelectedProviderId: (value: string) => void;
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
  const [providerOptions, setProviderOptions] = useState<PlatformProvider[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [providerLoadError, setProviderLoadError] = useState("");
  const [providersLoading, setProvidersLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const enabledVectorProviders = useMemo(
    () => providerOptions.filter((provider) => provider.capability === "vector_store" && provider.enabled),
    [providerOptions],
  );

  useEffect(() => {
    if (!token) {
      setProvidersLoading(false);
      return;
    }
    const loadProviders = async (): Promise<void> => {
      setProvidersLoading(true);
      setProviderLoadError("");
      try {
        const providers = await listPlatformProviders(token);
        setProviderOptions(providers);
      } catch (requestError) {
        setProviderLoadError(requestError instanceof Error ? requestError.message : t("contextManagement.feedback.providerLoadFailed"));
      } finally {
        setProvidersLoading(false);
      }
    };
    void loadProviders();
  }, [t, token]);

  useEffect(() => {
    if (enabledVectorProviders.length === 1 && !selectedProviderId) {
      setSelectedProviderId(enabledVectorProviders[0].id);
    }
  }, [enabledVectorProviders, selectedProviderId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    if (!selectedProviderId) {
      showErrorFeedback(t("contextManagement.feedback.providerRequired"), t("contextManagement.feedback.createFailed"));
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
        backing_provider_instance_id: selectedProviderId,
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
    providerOptions: enabledVectorProviders,
    selectedProviderId,
    providerLoadError,
    providersLoading,
    saving,
    setSlug,
    setDisplayName,
    setDescription,
    setSchemaText,
    setSelectedProviderId,
    handleSubmit,
  };
}
