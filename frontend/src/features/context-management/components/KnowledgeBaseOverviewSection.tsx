import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase } from "../../../api/context";
import { KnowledgeBaseChunkingEditor } from "./KnowledgeBaseChunkingEditor";
import type { KnowledgeBaseOverviewFormState } from "../types";

type Props = {
  knowledgeBase: KnowledgeBase;
  form: KnowledgeBaseOverviewFormState;
  isSuperadmin: boolean;
  isResyncing: boolean;
  onFormChange: Dispatch<SetStateAction<KnowledgeBaseOverviewFormState>>;
  onSave: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onDelete: () => Promise<void>;
  onResync: () => Promise<void>;
};

export function KnowledgeBaseOverviewSection({
  knowledgeBase,
  form,
  isSuperadmin,
  isResyncing,
  onFormChange,
  onSave,
  onDelete,
  onResync,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <div className="status-row">
        <span className="platform-badge" data-tone={knowledgeBase.sync_status === "ready" ? "enabled" : "disabled"}>
          {`${knowledgeBase.lifecycle_state} / ${knowledgeBase.sync_status}`}
        </span>
        <span className="status-text">{knowledgeBase.index_name}</span>
      </div>
      <div className="card-stack">
        {knowledgeBase.backing_provider ? (
          <p className="status-text">
            {t("contextManagement.fields.provider")}: {knowledgeBase.backing_provider.display_name ?? knowledgeBase.backing_provider.id}
            {knowledgeBase.backing_provider.provider_key ? ` (${knowledgeBase.backing_provider.provider_key})` : ""}
          </p>
        ) : null}
        {knowledgeBase.deployment_usage?.length ? (
          <div className="card-stack">
            <p className="status-text">{t("contextManagement.usageTitle")}</p>
            {knowledgeBase.deployment_usage.map((usage) => (
              <p key={`${usage.deployment_profile.id}-${usage.capability}`} className="status-text">
                <strong>{usage.deployment_profile.display_name}</strong> ({usage.deployment_profile.slug}) - {usage.capability}
              </p>
            ))}
          </div>
        ) : null}
        <p className="status-text">
          {t("contextManagement.advancedSettings.vectorizationMode")}: {" "}
          {knowledgeBase.vectorization.mode === "self_provided"
            ? t("contextManagement.advancedSettings.selfProvided")
            : t("contextManagement.advancedSettings.vanessaEmbeddings")}
        </p>
        {knowledgeBase.vectorization.embedding_provider ? (
          <p className="status-text">
            {t("contextManagement.advancedSettings.embeddingProvider")}: {" "}
            {knowledgeBase.vectorization.embedding_provider.display_name ?? knowledgeBase.vectorization.embedding_provider.id}
          </p>
        ) : null}
        {knowledgeBase.vectorization.embedding_resource ? (
          <p className="status-text">
            {t("contextManagement.advancedSettings.embeddingModel")}: {" "}
            {knowledgeBase.vectorization.embedding_resource.display_name ?? knowledgeBase.vectorization.embedding_resource.id}
          </p>
        ) : null}
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkingStrategy")}: {" "}
          {knowledgeBase.chunking.strategy === "fixed_length"
            ? t("contextManagement.advancedSettings.fixedLength")
            : knowledgeBase.chunking.strategy}
        </p>
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkUnit")}: {" "}
          {knowledgeBase.chunking.config.unit === "tokens"
            ? t("contextManagement.advancedSettings.tokens")
            : knowledgeBase.chunking.config.unit}
        </p>
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkLength")}: {knowledgeBase.chunking.config.chunk_length}
        </p>
        <p className="status-text">
          {t("contextManagement.advancedSettings.chunkOverlap")}: {knowledgeBase.chunking.config.chunk_overlap}
        </p>
        <p className="status-text">
          {knowledgeBase.eligible_for_binding
            ? t("contextManagement.states.eligible")
            : t("contextManagement.states.ineligible")}
        </p>
        {knowledgeBase.last_sync_summary ? <p className="status-text">{knowledgeBase.last_sync_summary}</p> : null}
        {knowledgeBase.last_sync_at ? (
          <p className="status-text">
            {t("contextManagement.fields.lastSyncAt")}: {knowledgeBase.last_sync_at}
          </p>
        ) : null}
        {knowledgeBase.last_sync_error ? (
          <p className="status-text error-text">
            {t("contextManagement.fields.lastSyncError")}: {knowledgeBase.last_sync_error}
          </p>
        ) : null}
      </div>
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
            <button type="button" className="btn btn-danger" onClick={() => void onDelete()}>
              {t("contextManagement.actions.delete")}
            </button>
          </div>
        ) : null}
      </form>
    </section>
  );
}
