import { useRef, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase } from "../../../api/context";
import ModalDialog from "../../../components/ModalDialog";
import { KnowledgeBaseChunkingEditor } from "./KnowledgeBaseChunkingEditor";
import type { KnowledgeBaseOverviewFormState } from "../types";

type Props = {
  knowledgeBase: KnowledgeBase;
  form: KnowledgeBaseOverviewFormState;
  isDeleteDialogOpen: boolean;
  isDeleting: boolean;
  isSuperadmin: boolean;
  isResyncing: boolean;
  onFormChange: Dispatch<SetStateAction<KnowledgeBaseOverviewFormState>>;
  onCloseDeleteDialog: () => void;
  onConfirmDelete: () => Promise<void>;
  onOpenDeleteDialog: () => void;
  onSave: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onResync: () => Promise<void>;
};

type SummaryCardProps = {
  label: string;
  value: string;
  secondary?: string | null;
};

function SummaryCard({ label, value, secondary = null }: SummaryCardProps): JSX.Element {
  return (
    <article className="platform-summary-card context-kb-summary-card">
      <span className="field-label">{label}</span>
      <strong className="context-kb-summary-value">{value}</strong>
      {secondary ? <span className="status-text">{secondary}</span> : null}
    </article>
  );
}

export function KnowledgeBaseOverviewSection({
  knowledgeBase,
  form,
  isDeleteDialogOpen,
  isDeleting,
  isSuperadmin,
  isResyncing,
  onFormChange,
  onCloseDeleteDialog,
  onConfirmDelete,
  onOpenDeleteDialog,
  onSave,
  onResync,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const noneLabel = t("platformControl.summary.none");
  const vectorizationModeLabel =
    knowledgeBase.vectorization.mode === "self_provided"
      ? t("contextManagement.advancedSettings.selfProvided")
      : t("contextManagement.advancedSettings.vanessaEmbeddings");
  const chunkingStrategyLabel =
    knowledgeBase.chunking.strategy === "fixed_length"
      ? t("contextManagement.advancedSettings.fixedLength")
      : knowledgeBase.chunking.strategy;
  const chunkUnitLabel =
    knowledgeBase.chunking.config.unit === "tokens"
      ? t("contextManagement.advancedSettings.tokens")
      : knowledgeBase.chunking.config.unit;
  const deploymentEligibilityLabel = knowledgeBase.eligible_for_binding
    ? t("contextManagement.states.eligible")
    : t("contextManagement.states.ineligible");
  const backingProviderValue = knowledgeBase.backing_provider?.display_name ?? knowledgeBase.backing_provider?.id ?? noneLabel;
  const backingProviderSecondary =
    knowledgeBase.backing_provider?.provider_key && knowledgeBase.backing_provider.provider_key !== backingProviderValue
      ? knowledgeBase.backing_provider.provider_key
      : null;
  const embeddingProviderValue =
    knowledgeBase.vectorization.embedding_provider?.display_name ??
    knowledgeBase.vectorization.embedding_provider?.id ??
    noneLabel;
  const embeddingProviderSecondary =
    knowledgeBase.vectorization.embedding_provider?.provider_key &&
    knowledgeBase.vectorization.embedding_provider.provider_key !== embeddingProviderValue
      ? knowledgeBase.vectorization.embedding_provider.provider_key
      : null;
  const embeddingModelValue =
    knowledgeBase.vectorization.embedding_resource?.display_name ??
    knowledgeBase.vectorization.embedding_resource?.id ??
    noneLabel;
  const embeddingModelSecondary =
    knowledgeBase.vectorization.embedding_resource?.provider_resource_id &&
    knowledgeBase.vectorization.embedding_resource.provider_resource_id !== embeddingModelValue
      ? knowledgeBase.vectorization.embedding_resource.provider_resource_id
      : null;

  return (
    <section className="panel card-stack">
      <div className="status-row">
        <span className="platform-badge" data-tone={knowledgeBase.sync_status === "ready" ? "enabled" : "disabled"}>
          {`${knowledgeBase.lifecycle_state} / ${knowledgeBase.sync_status}`}
        </span>
        <span className="status-text">{knowledgeBase.index_name}</span>
      </div>
      <div className="platform-detail-grid context-kb-summary-grid">
        <SummaryCard
          label={t("contextManagement.fields.provider")}
          value={backingProviderValue}
          secondary={backingProviderSecondary}
        />
        <article className="platform-summary-card context-kb-summary-card">
          <span className="field-label">{t("contextManagement.usageTitle")}</span>
          {knowledgeBase.deployment_usage?.length ? (
            <ul className="context-kb-summary-list">
              {knowledgeBase.deployment_usage.map((usage) => (
                <li key={`${usage.deployment_profile.id}-${usage.capability}`} className="context-kb-summary-list-item">
                  <strong className="context-kb-summary-list-primary">{usage.deployment_profile.display_name}</strong>
                  <span className="status-text context-kb-summary-list-secondary">
                    {usage.deployment_profile.slug} · {usage.capability}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <strong className="context-kb-summary-value">{noneLabel}</strong>
          )}
        </article>
        <SummaryCard label={t("contextManagement.advancedSettings.vectorizationMode")} value={vectorizationModeLabel} />
        <SummaryCard
          label={t("contextManagement.advancedSettings.embeddingProvider")}
          value={embeddingProviderValue}
          secondary={embeddingProviderSecondary}
        />
        <SummaryCard
          label={t("contextManagement.advancedSettings.embeddingModel")}
          value={embeddingModelValue}
          secondary={embeddingModelSecondary}
        />
        <SummaryCard label={t("contextManagement.advancedSettings.chunkingStrategy")} value={chunkingStrategyLabel} />
        <SummaryCard label={t("contextManagement.advancedSettings.chunkUnit")} value={chunkUnitLabel} />
        <SummaryCard
          label={t("contextManagement.advancedSettings.chunkLength")}
          value={String(knowledgeBase.chunking.config.chunk_length)}
        />
        <SummaryCard
          label={t("contextManagement.advancedSettings.chunkOverlap")}
          value={String(knowledgeBase.chunking.config.chunk_overlap)}
        />
        <SummaryCard label={t("contextManagement.fields.deploymentEligibility")} value={deploymentEligibilityLabel} />
        <SummaryCard label={t("contextManagement.fields.lastSyncAt")} value={knowledgeBase.last_sync_at ?? noneLabel} />
      </div>
      {knowledgeBase.last_sync_summary ? <p className="status-text context-kb-summary-callout">{knowledgeBase.last_sync_summary}</p> : null}
      {knowledgeBase.last_sync_error ? (
        <p className="status-text error-text context-kb-summary-callout">
          {t("contextManagement.fields.lastSyncError")}: {knowledgeBase.last_sync_error}
        </p>
      ) : null}
      {isSuperadmin ? (
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" disabled={isResyncing} onClick={() => void onResync()}>
            {isResyncing ? t("contextManagement.actions.resyncing") : t("contextManagement.actions.resync")}
          </button>
        </div>
      ) : null}
      <form className="card-stack" onSubmit={(event) => void onSave(event)}>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
          <input
            className="field-input"
            value={form.slug}
            disabled={!isSuperadmin}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onFormChange((current) => ({ ...current, slug: value }));
            }}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
          <input
            className="field-input"
            value={form.displayName}
            disabled={!isSuperadmin}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onFormChange((current) => ({ ...current, displayName: value }));
            }}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
          <textarea
            className="field-input quote-admin-textarea"
            value={form.description}
            disabled={!isSuperadmin}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onFormChange((current) => ({ ...current, description: value }));
            }}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.fields.lifecycleState")}</span>
          <select
            className="field-input"
            value={form.lifecycleState}
            disabled={!isSuperadmin}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onFormChange((current) => ({ ...current, lifecycleState: value }));
            }}
          >
            <option value="active">active</option>
            <option value="archived">archived</option>
          </select>
        </label>
        {knowledgeBase.document_count === 0 ? (
          <KnowledgeBaseChunkingEditor
            form={form.chunking}
            editable={isSuperadmin}
            showInputsWhenReadOnly={!isSuperadmin}
            editabilityMessage="editable_before_ingest"
            onChangeField={(field, value) => {
              onFormChange((current) => ({
                ...current,
                chunking: {
                  ...current.chunking,
                  [field]: value,
                },
              }));
            }}
          />
        ) : (
          <KnowledgeBaseChunkingEditor
            form={form.chunking}
            editable={false}
            editabilityMessage="locked_after_ingest"
          />
        )}
        {isSuperadmin ? (
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              {t("contextManagement.actions.save")}
            </button>
            <button type="button" className="btn btn-danger" onClick={onOpenDeleteDialog}>
              {t("contextManagement.actions.delete")}
            </button>
          </div>
        ) : null}
      </form>
      {isDeleteDialogOpen ? (
        <ModalDialog
          eyebrow={t("contextManagement.deleteDialog.eyebrow")}
          title={t("contextManagement.deleteDialog.title")}
          description={t("contextManagement.deleteDialog.description", { name: knowledgeBase.display_name })}
          onClose={onCloseDeleteDialog}
          closeDisabled={isDeleting}
          initialFocusRef={confirmButtonRef}
          actions={(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onCloseDeleteDialog}
                disabled={isDeleting}
              >
                {t("contextManagement.actions.cancel")}
              </button>
              <button
                ref={confirmButtonRef}
                type="button"
                className="btn btn-danger"
                onClick={() => void onConfirmDelete()}
                disabled={isDeleting}
              >
                {t("contextManagement.deleteDialog.confirm")}
              </button>
            </>
          )}
        />
      ) : null}
    </section>
  );
}
