import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listModelOpsModels, registerManagedModel } from "../../../api/modelops/models";
import { createModelCredential, listModelCredentials, revokeModelCredential } from "../../../api/modelops/credentials";
import type { ManagedModel, ModelCredential } from "../../../api/modelops/types";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

export function useCloudRegistrationFlow(
  token: string,
): {
  credentials: ModelCredential[];
  recentCloudModels: ManagedModel[];
  isLoading: boolean;
  isSaving: boolean;
  refresh: () => Promise<void>;
  saveCredential: (payload: {
    provider: string;
    display_name?: string;
    api_base_url?: string;
    api_key: string;
    credential_scope?: "platform" | "personal";
  }) => Promise<void>;
  revokeCredential: (credentialId: string) => Promise<void>;
  registerCloudModel: (payload: {
    id: string;
    name: string;
    provider: string;
    owner_type?: "platform" | "user";
    visibility_scope?: "private" | "user" | "group" | "platform";
    provider_model_id: string;
    credential_id?: string;
    task_key: string;
    category?: "predictive" | "generative";
    comment?: string;
  }) => Promise<ManagedModel | null>;
} {
  const [credentials, setCredentials] = useState<ModelCredential[]>([]);
  const [recentCloudModels, setRecentCloudModels] = useState<ManagedModel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    try {
      const [credentialRows, modelRows] = await Promise.all([
        listModelCredentials(token),
        listModelOpsModels(token),
      ]);
      setCredentials(credentialRows);
      setRecentCloudModels(modelRows.filter((model) => model.backend === "external_api").slice(0, 6));
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.cloud.loadFailed"), {
        titleKey: "modelOps.cloud.title",
      });
    } finally {
      setIsLoading(false);
    }
  }, [showErrorFeedback, t, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveCredential = useCallback(async (payload: {
    provider: string;
    display_name?: string;
    api_base_url?: string;
    api_key: string;
    credential_scope?: "platform" | "personal";
  }): Promise<void> => {
    if (!token) {
      return;
    }
    setIsSaving(true);
    try {
      await createModelCredential(payload, token);
      showSuccessFeedback(t("modelOps.cloud.credentialSaved"), {
        titleKey: "modelOps.cloud.credentialsTitle",
      });
      await refresh();
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.cloud.credentialSaveFailed"), {
        titleKey: "modelOps.cloud.credentialsTitle",
      });
    } finally {
      setIsSaving(false);
    }
  }, [refresh, showErrorFeedback, showSuccessFeedback, t, token]);

  const revokeCredential = useCallback(async (credentialId: string): Promise<void> => {
    if (!token) {
      return;
    }
    setIsSaving(true);
    try {
      await revokeModelCredential(credentialId, token);
      showSuccessFeedback(t("modelOps.cloud.credentialRevoked"), {
        titleKey: "modelOps.cloud.credentialsTitle",
      });
      await refresh();
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.cloud.credentialRevokeFailed"), {
        titleKey: "modelOps.cloud.credentialsTitle",
      });
    } finally {
      setIsSaving(false);
    }
  }, [refresh, showErrorFeedback, showSuccessFeedback, t, token]);

  const registerCloudModel = useCallback(async (payload: {
    id: string;
    name: string;
    provider: string;
    owner_type?: "platform" | "user";
    visibility_scope?: "private" | "user" | "group" | "platform";
    provider_model_id: string;
    credential_id?: string;
    task_key: string;
    category?: "predictive" | "generative";
    comment?: string;
  }): Promise<ManagedModel | null> => {
    if (!token) {
      return null;
    }
    setIsSaving(true);
    try {
      const created = await registerManagedModel(
        {
          id: payload.id,
          name: payload.name,
          provider: payload.provider,
          backend: "external_api",
          owner_type: payload.owner_type,
          source: "external_provider",
          availability: "online_only",
          visibility_scope: payload.visibility_scope,
          provider_model_id: payload.provider_model_id,
          credential_id: payload.credential_id,
          task_key: payload.task_key,
          category: payload.category,
          comment: payload.comment,
        },
        token,
      );
      showSuccessFeedback(t("modelOps.cloud.modelRegistered"), {
        titleKey: "modelOps.cloud.registrationTitle",
      });
      await refresh();
      return created;
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.cloud.modelRegisterFailed"), {
        titleKey: "modelOps.cloud.registrationTitle",
      });
      return null;
    } finally {
      setIsSaving(false);
    }
  }, [refresh, showErrorFeedback, showSuccessFeedback, t, token]);

  return {
    credentials,
    recentCloudModels,
    isLoading,
    isSaving,
    refresh,
    saveCredential,
    revokeCredential,
    registerCloudModel,
  };
}
