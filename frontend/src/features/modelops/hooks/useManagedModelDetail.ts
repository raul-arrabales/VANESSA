import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

export function useManagedModelDetail(
  modelId: string | undefined,
  token: string,
): {
  model: ManagedModel | null;
  usage: ModelUsageSummary | null;
  validations: ModelValidationRecord[];
  isLoading: boolean;
  isMutating: boolean;
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
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();

  const refresh = useCallback(async (): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsLoading(true);

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
      showErrorFeedback(requestError, t("modelOps.detail.loadFailed"), {
        titleKey: "modelOps.detail.title",
      });
    } finally {
      setIsLoading(false);
    }
  }, [modelId, showErrorFeedback, t, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runMutation(
    action: () => Promise<unknown>,
    successMessageKey: string,
  ): Promise<void> {
    setIsMutating(true);
    try {
      await action();
      showSuccessFeedback(t(successMessageKey), {
        titleKey: "modelOps.detail.title",
      });
      await refresh();
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.detail.updateFailed"), {
        titleKey: "modelOps.detail.title",
      });
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
    refresh,
    register: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => registerExistingManagedModel(modelId, token), "modelOps.detail.registered");
    },
    activate: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => activateManagedModel(modelId, token), "modelOps.detail.activated");
    },
    deactivate: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => deactivateManagedModel(modelId, token), "modelOps.detail.deactivated");
    },
    unregister: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => unregisterManagedModel(modelId, token), "modelOps.detail.unregistered");
    },
    remove: async () => {
      if (!token || !modelId) {
        return;
      }
      await runMutation(() => deleteManagedModel(modelId, token), "modelOps.detail.deleted");
    },
  };
}
