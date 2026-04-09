import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { registerManagedModel } from "../../../api/modelops/models";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

type LocalModelRegistrationPayload = {
  id: string;
  name: string;
  provider: string;
  localPath: string;
  taskKey: string;
  category: "predictive" | "generative";
  comment: string;
};

export function useLocalModelRegistration(token: string): {
  lastRegisteredModelId: string;
  registerLocalModel: (payload: LocalModelRegistrationPayload) => Promise<boolean>;
} {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [lastRegisteredModelId, setLastRegisteredModelId] = useState("");

  const registerLocalModel = useCallback(async (payload: LocalModelRegistrationPayload): Promise<boolean> => {
    if (!token) {
      return false;
    }

    try {
      const model = await registerManagedModel(
        {
          id: payload.id.trim(),
          name: payload.name.trim(),
          provider: payload.provider.trim() || "local",
          backend: "local",
          owner_type: "platform",
          source: "local_folder",
          availability: "offline_ready",
          visibility_scope: "platform",
          local_path: payload.localPath.trim(),
          task_key: payload.taskKey,
          category: payload.category,
          comment: payload.comment.trim() || undefined,
        },
        token,
      );
      setLastRegisteredModelId(model.id);
      showSuccessFeedback(t("modelOps.local.manualSuccess"), {
        titleKey: "modelOps.local.manualTitle",
      });
      return true;
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.local.manualFailure"), {
        titleKey: "modelOps.local.manualTitle",
      });
      return false;
    }
  }, [showErrorFeedback, showSuccessFeedback, t, token]);

  return {
    lastRegisteredModelId,
    registerLocalModel,
  };
}
