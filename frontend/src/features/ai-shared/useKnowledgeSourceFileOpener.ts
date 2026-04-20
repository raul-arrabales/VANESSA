import { type MouseEvent, useCallback } from "react";
import { useTranslation } from "react-i18next";
import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";
import { buildUrl } from "../../auth/authApi";
import { readStoredToken } from "../../auth/storage";
import { useActionFeedback } from "../../feedback/ActionFeedbackProvider";
import { firstPageFragment } from "./knowledgeReferenceLinks";

export function useKnowledgeSourceFileOpener(): (
  event: MouseEvent<HTMLAnchorElement>,
  reference: PlaygroundKnowledgeReference,
) => Promise<void> {
  const { t } = useTranslation("common");
  const { showErrorFeedback } = useActionFeedback();

  return useCallback(
    async (event: MouseEvent<HTMLAnchorElement>, reference: PlaygroundKnowledgeReference): Promise<void> => {
      if (!reference.file_url) {
        return;
      }
      event.preventDefault();
      const token = readStoredToken();
      if (!token) {
        showErrorFeedback(t("playgrounds.references.openSourceAuthRequired"));
        return;
      }
      const targetWindow = window.open("about:blank", "_blank");
      if (!targetWindow) {
        showErrorFeedback(t("playgrounds.references.openSourcePopupBlocked"));
        return;
      }
      targetWindow.opener = null;
      try {
        const response = await fetch(buildUrl(reference.file_url), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error(t("playgrounds.references.openSourceFailed"));
        }
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        targetWindow.location.href = `${objectUrl}${firstPageFragment(reference)}`;
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      } catch (error) {
        targetWindow.close();
        showErrorFeedback(error, t("playgrounds.references.openSourceFailed"));
      }
    },
    [showErrorFeedback, t],
  );
}
