import { useCallback, useEffect, useState } from "react";
import {
  activateManagedModel,
  deactivateManagedModel,
  deleteManagedModel,
  getManagedModel,
  getManagedModelUsage,
  getManagedModelValidations,
  registerExistingManagedModel,
  unregisterManagedModel,
} from "../../../api/modelops/models";
import type { ManagedModel, ModelUsageSummary, ModelValidationRecord } from "../../../api/modelops/types";

export function useManagedModelDetail(
  modelId: string | undefined,
  token: string,
): {
  model: ManagedModel | null;
  usage: ModelUsageSummary | null;
  validations: ModelValidationRecord[];
  isLoading: boolean;
  isMutating: boolean;
  error: string;
  feedback: string;
  refresh: () => Promise<void>;
  register: () => Promise<void>;
  activate: () => Promise<void>;
  deactivate: () => Promise<void>;
  unregister: () => Promise<void>;
  remove: () => Promise<void>;
} {
  const [model, setModel] = useState<ManagedModel | null>(null);
  const [usage, setUsage] = useState<ModelUsageSummary | null>(null);
  const [validations, setValidations] = useState<ModelValidationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const [modelPayload, usagePayload, validationPayload] = await Promise.all([
        getManagedModel(modelId, token),
        getManagedModelUsage(modelId, token),
        getManagedModelValidations(modelId, token),
      ]);
      setModel(modelPayload);
      setUsage(usagePayload.usage ?? modelPayload.usage_summary ?? null);
      setValidations(validationPayload.validations);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load model details.");
    } finally {
      setIsLoading(false);
    }
  }, [modelId, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runMutation(
    action: () => Promise<unknown>,
    successMessage: string,
  ): Promise<void> {
    setIsMutating(true);
    setError("");
    setFeedback("");
    try {
      await action();
      setFeedback(successMessage);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update model.");
    } finally {
      setIsMutating(false);
    }
  }

  return {
    model,
    usage,
    validations,
    isLoading,
    isMutating,
    error,
    feedback,
    refresh,
    register: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => registerExistingManagedModel(modelId, token), "Model registered.");
    },
    activate: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => activateManagedModel(modelId, token), "Model activated.");
    },
    deactivate: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => deactivateManagedModel(modelId, token), "Model deactivated.");
    },
    unregister: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => unregisterManagedModel(modelId, token), "Model unregistered.");
    },
    remove: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => deleteManagedModel(modelId, token), "Model deleted.");
    },
  };
}
