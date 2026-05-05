import { useRef } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { PlaygroundKnowledgeBaseOption } from "../../../api/playgrounds";
import type { PlaygroundSelectorKind } from "../types";
import KnowledgeBaseSelector from "./KnowledgeBaseSelector";
import ModelSelector from "./ModelSelector";

type PlaygroundSettingsDialogProps = {
  selectors: PlaygroundSelectorKind[];
  models: Array<{ id: string; displayName: string }>;
  knowledgeBases: PlaygroundKnowledgeBaseOption[];
  modelValue: string;
  knowledgeBaseValue: string;
  isModelLoading: boolean;
  isKnowledgeBaseLoading: boolean;
  isModelDisabled: boolean;
  isKnowledgeBaseDisabled: boolean;
  onModelChange: (value: string) => void;
  onKnowledgeBaseChange: (value: string) => void;
  onClose: () => void;
};

export default function PlaygroundSettingsDialog({
  selectors,
  models,
  knowledgeBases,
  modelValue,
  knowledgeBaseValue,
  isModelLoading,
  isKnowledgeBaseLoading,
  isModelDisabled,
  isKnowledgeBaseDisabled,
  onModelChange,
  onKnowledgeBaseChange,
  onClose,
}: PlaygroundSettingsDialogProps): JSX.Element {
  const { t } = useTranslation("common");
  const modelSelectRef = useRef<HTMLSelectElement>(null);
  const knowledgeBaseSelectRef = useRef<HTMLSelectElement>(null);
  const hasModelSelector = selectors.includes("model");
  const hasKnowledgeBaseSelector = selectors.includes("knowledgeBase");
  const initialFocusRef = hasModelSelector ? modelSelectRef : knowledgeBaseSelectRef;

  return (
    <ModalDialog
      className="playground-session-dialog"
      title={t("playgroundSessionSettings.title")}
      description={t("playgroundSessionSettings.description")}
      onClose={onClose}
      initialFocusRef={initialFocusRef}
      actions={(
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onClose}
        >
          {t("playgroundSessionSettings.close")}
        </button>
      )}
    >
      <div className="control-group playground-session-settings-fields">
        {hasModelSelector ? (
          <ModelSelector
            selectRef={modelSelectRef}
            models={models}
            value={modelValue}
            isLoading={isModelLoading}
            disabled={isModelDisabled}
            onChange={onModelChange}
          />
        ) : null}
        {hasKnowledgeBaseSelector ? (
          <KnowledgeBaseSelector
            selectRef={knowledgeBaseSelectRef}
            knowledgeBases={knowledgeBases}
            value={knowledgeBaseValue}
            isLoading={isKnowledgeBaseLoading}
            disabled={isKnowledgeBaseDisabled}
            onChange={onKnowledgeBaseChange}
          />
        ) : null}
      </div>
    </ModalDialog>
  );
}
