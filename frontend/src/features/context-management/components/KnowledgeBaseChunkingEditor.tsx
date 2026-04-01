import { useTranslation } from "react-i18next";
import type { KnowledgeBaseEmbeddingResourceSummary } from "../../../api/context";
import type { ChunkingFormState } from "../chunkingForm";

type Props = {
  form: ChunkingFormState;
  editable: boolean;
  disabled?: boolean;
  showInputsWhenReadOnly?: boolean;
  showStrategySelector?: boolean;
  showDescription?: boolean;
  showUnitLabel?: boolean;
  constraints?: KnowledgeBaseEmbeddingResourceSummary["chunking_constraints"] | null;
  showConstraintsHint?: boolean;
  inlineSafeLimitErrorMessage?: string | null;
  editabilityMessage?: "editable_before_ingest" | "locked_after_ingest" | null;
  onChangeField?: (field: keyof ChunkingFormState, value: string) => void;
};

export function KnowledgeBaseChunkingEditor({
  form,
  editable,
  disabled = false,
  showInputsWhenReadOnly = false,
  showStrategySelector = false,
  showDescription = false,
  showUnitLabel = false,
  constraints = null,
  showConstraintsHint = false,
  inlineSafeLimitErrorMessage = null,
  editabilityMessage = null,
  onChangeField,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <div className="card-stack">
      {showStrategySelector ? (
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.advancedSettings.chunkingStrategy")}</span>
          <select
            className="field-input"
            value={form.strategy}
            disabled={!editable || disabled}
            onChange={(event) => onChangeField?.("strategy", event.currentTarget.value)}
          >
            <option value="fixed_length">{t("contextManagement.advancedSettings.fixedLength")}</option>
          </select>
        </label>
      ) : null}
      {showDescription ? <p className="status-text">{t("contextManagement.advancedSettings.chunkingDescription")}</p> : null}
      {showUnitLabel ? (
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkUnit")}: {t("contextManagement.advancedSettings.tokens")}
        </p>
      ) : null}
      {editabilityMessage === "editable_before_ingest" ? (
        <p className="status-text">{t("contextManagement.states.chunkingEditableBeforeIngest")}</p>
      ) : null}
      {showConstraintsHint && constraints ? (
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkLimitHint", {
            safeChunkLengthMax: constraints.safe_chunk_length_max,
            maxInputTokens: constraints.max_input_tokens,
            specialTokensPerInput: constraints.special_tokens_per_input,
          })}
        </p>
      ) : null}
      {editable || showInputsWhenReadOnly ? (
        <>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.advancedSettings.chunkLength")}</span>
            <input
              className="field-input"
              inputMode="numeric"
              type="number"
              min={1}
              step={1}
              value={form.chunkLength}
              disabled={!editable || disabled}
              onChange={(event) => onChangeField?.("chunkLength", event.currentTarget.value)}
            />
          </label>
          {editable && inlineSafeLimitErrorMessage ? (
            <p className="status-text error-text">{inlineSafeLimitErrorMessage}</p>
          ) : null}
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.advancedSettings.chunkOverlap")}</span>
            <input
              className="field-input"
              inputMode="numeric"
              type="number"
              min={0}
              step={1}
              value={form.chunkOverlap}
              disabled={!editable || disabled}
              onChange={(event) => onChangeField?.("chunkOverlap", event.currentTarget.value)}
            />
          </label>
        </>
      ) : null}
      {!editable && editabilityMessage === "locked_after_ingest" ? (
        <p className="status-text">{t("contextManagement.states.chunkingLockedAfterIngest")}</p>
      ) : null}
    </div>
  );
}
