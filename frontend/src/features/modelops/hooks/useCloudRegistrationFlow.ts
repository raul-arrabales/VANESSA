import { useCallback, useEffect, useState } from "react";
import {
  createModelCredential,
  listModelCredentials,
  listModelOpsModels,
  registerManagedModel,
  validateManagedModel,
  type ManagedModel,
  type ModelCredential,
} from "../../../api/models";

export function useCloudRegistrationFlow(
  token: string,
): {
  credentials: ModelCredential[];
  recentCloudModels: ManagedModel[];
  isLoading: boolean;
  isSaving: boolean;
  error: string;
  feedback: string;
  refresh: () => Promise<void>;
  saveCredential: (payload: {
    provider: string;
    display_name?: string;
    api_base_url?: string;
    api_key: string;
    credential_scope?: "platform" | "personal";
  }) => Promise<void>;
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
    validate_after_register?: boolean;
  }) => Promise<void>;
} {
  const [credentials, setCredentials] = useState<ModelCredential[]>([]);
  const [recentCloudModels, setRecentCloudModels] = useState<ManagedModel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const [credentialRows, modelRows] = await Promise.all([
        listModelCredentials(token),
        listModelOpsModels(token),
      ]);
      setCredentials(credentialRows);
      setRecentCloudModels(modelRows.filter((model) => model.backend === "external_api").slice(0, 6));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load cloud registration data.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

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
    setError("");
    setFeedback("");
    try {
      await createModelCredential(payload, token);
      setFeedback("Credential saved.");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save credential.");
    } finally {
      setIsSaving(false);
    }
  }, [refresh, token]);

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
    validate_after_register?: boolean;
  }): Promise<void> => {
    if (!token) {
      return;
    }
    setIsSaving(true);
    setError("");
    setFeedback("");
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
      if (payload.validate_after_register) {
        await validateManagedModel(created.id, token);
      }
      setFeedback(payload.validate_after_register ? "Model registered and validated." : "Model registered.");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to register cloud model.");
    } finally {
      setIsSaving(false);
    }
  }, [refresh, token]);

  return {
    credentials,
    recentCloudModels,
    isLoading,
    isSaving,
    error,
    feedback,
    refresh,
    saveCredential,
    registerCloudModel,
  };
}
