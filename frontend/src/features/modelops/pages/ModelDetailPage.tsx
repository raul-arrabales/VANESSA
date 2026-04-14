import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import ModelCatalogSubmenu from "../components/ModelCatalogSubmenu";
import ModelLifecycleActions from "../components/ModelLifecycleActions";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import UsageSummaryPanel from "../components/UsageSummaryPanel";
import ValidationHistoryPanel from "../components/ValidationHistoryPanel";
import { useManagedModelDetail } from "../hooks/useManagedModelDetail";
import { CLOUD_PROVIDER_OPTIONS, canAccessModelTesting, getModelLifecyclePermissions, isModelTestEligible } from "../domain";

export default function ModelDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { modelId } = useParams();
  const { token, user } = useAuth();
  const detail = useManagedModelDetail(modelId, token);
  const permissions = getModelLifecyclePermissions(user, detail.model);
  const canTest = canAccessModelTesting(user);
  const [replacementCredentialId, setReplacementCredentialId] = useState("");
  const modelName = detail.model?.name ?? modelId ?? "";
  const modelDetailSubmenu = (
    <ModelCatalogSubmenu
      activeView="detail"
      modelId={detail.model?.id ?? modelId}
      modelName={modelName}
      showDetailView
      showTestView={Boolean(detail.model && canTest && isModelTestEligible(detail.model))}
    />
  );

  if (detail.isLoading) {
    return (
      <ModelOpsWorkspaceFrame secondaryNavigation={modelDetailSubmenu}>
        <p className="status-text">{t("modelOps.states.loading")}</p>
      </ModelOpsWorkspaceFrame>
    );
  }

  if (!detail.model) {
    return (
      <ModelOpsWorkspaceFrame secondaryNavigation={modelDetailSubmenu}>
        <section className="panel card-stack">
          <h2 className="section-title">{t("modelOps.detail.title")}</h2>
          <p className="status-text">{t("modelOps.detail.notFound")}</p>
        </section>
      </ModelOpsWorkspaceFrame>
    );
  }

  const model = detail.model;
  const credentialStatus = model.credential?.status ?? (model.backend === "external_api" ? "missing" : "not_required");
  const canReplaceCredential =
    model.backend === "external_api"
    && credentialStatus !== "not_required"
    && (user?.role === "superadmin" || (user?.role === "user" && model.owner_type === "user" && model.owner_user_id === user.id));
  const matchingCredentials = detail.credentials.filter(
    (credential) => credential.provider === model.provider && credential.id !== model.credential?.id,
  );
  const providerOption = CLOUD_PROVIDER_OPTIONS.find((option) => option.value === model.provider);
  const providerLabel = providerOption ? t(providerOption.labelKey) : model.provider;

  function handleCredentialSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void detail.replaceCredential(replacementCredentialId);
  }

  return (
    <ModelOpsWorkspaceFrame secondaryNavigation={modelDetailSubmenu}>
      <section className="card-stack">
      <article className="panel card-stack">
        <div className="modelops-card-header">
          <div className="card-stack">
            <h2 className="section-title">{model.name}</h2>
            <p className="status-text">{model.id}</p>
          </div>
          <div className="button-row">
            {(user?.role === "admin" || user?.role === "superadmin") && (
              <Link className="btn btn-secondary" to={`/control/models/access?modelId=${encodeURIComponent(model.id)}`}>
                {t("modelOps.actions.manageAccess")}
              </Link>
            )}
          </div>
        </div>
        <p className="status-text">
          {`${model.provider} · ${model.task_key ?? "unknown"} · ${model.lifecycle_state ?? "unknown"} · ${model.hosting ?? model.backend}`}
        </p>
        <p className="status-text">
          {`${model.owner_type ?? "unknown"} · ${model.visibility_scope ?? "private"} · Validation: ${model.last_validation_status ?? "pending"}`}
        </p>
        <ModelLifecycleActions
          model={model}
          permissions={permissions}
          isPending={detail.isMutating}
          onRegister={detail.register}
          onActivate={detail.activate}
          onDeactivate={detail.deactivate}
          onUnregister={detail.unregister}
          onDelete={detail.remove}
        />
      </article>

      {model.backend === "external_api" && credentialStatus !== "not_required" ? (
        <article className="panel card-stack">
          <h2 className="section-title">{t("modelOps.detail.credentialTitle")}</h2>
          <p className="status-text">
            {`${t("modelOps.detail.credentialStatusLabel")}: ${t(`modelOps.detail.credentialStatuses.${credentialStatus}`)}`}
          </p>
          <p className="status-text">
            {model.credential?.display_name && model.credential.api_key_last4
              ? t("modelOps.detail.currentCredential", {
                  name: model.credential.display_name,
                  suffix: model.credential.api_key_last4,
                })
              : t("modelOps.detail.noCurrentCredential")}
          </p>
          {credentialStatus === "revoked" || credentialStatus === "missing" ? (
            <p className="status-text">{t("modelOps.detail.credentialReplacementRequired")}</p>
          ) : null}
          {canReplaceCredential ? (
            <form className="form-grid" onSubmit={handleCredentialSubmit}>
              <label className="field-label" htmlFor="replacement-credential-id">
                {t("modelOps.detail.replacementCredentialLabel", { provider: providerLabel })}
              </label>
              <select
                id="replacement-credential-id"
                className="input"
                value={replacementCredentialId}
                onChange={(event) => setReplacementCredentialId(event.currentTarget.value)}
                disabled={detail.isMutating || matchingCredentials.length === 0}
              >
                <option value="">
                  {matchingCredentials.length === 0
                    ? t("modelOps.detail.noReplacementCredentials")
                    : t("modelOps.cloud.selectCredential")}
                </option>
                {matchingCredentials.map((credential) => (
                  <option key={credential.id} value={credential.id}>
                    {`${credential.display_name} · ****${credential.api_key_last4}`}
                  </option>
                ))}
              </select>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={detail.isMutating || !replacementCredentialId}
              >
                {t("modelOps.detail.replaceCredential")}
              </button>
            </form>
          ) : null}
        </article>
      ) : null}

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.detail.metadataTitle")}</h2>
        <ul className="card-stack" aria-label={t("modelOps.detail.metadataAria")}>
          <li className="status-row"><span>{`${t("modelOps.fields.providerModelId")}: ${model.provider_model_id ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.source")}: ${model.source ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.localPath")}: ${model.artifact?.storage_path ?? model.metadata?.local_path ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.comment")}: ${model.comment ?? "--"}`}</span></li>
        </ul>
      </article>

      <UsageSummaryPanel usage={detail.usage} />
      <ValidationHistoryPanel validations={detail.validations} />
      </section>
    </ModelOpsWorkspaceFrame>
  );
}
