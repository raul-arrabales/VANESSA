import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import ModelLifecycleActions from "../components/ModelLifecycleActions";
import UsageSummaryPanel from "../components/UsageSummaryPanel";
import ValidationHistoryPanel from "../components/ValidationHistoryPanel";
import { useManagedModelDetail } from "../hooks/useManagedModelDetail";
import { canAccessModelTesting, getModelLifecyclePermissions } from "../domain";

export default function ModelDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { modelId } = useParams();
  const { token, user } = useAuth();
  const detail = useManagedModelDetail(modelId, token);
  const permissions = getModelLifecyclePermissions(user, detail.model);
  const canTest = canAccessModelTesting(user);

  if (detail.isLoading) {
    return <p className="status-text">{t("modelOps.states.loading")}</p>;
  }

  if (!detail.model) {
    return (
      <section className="panel card-stack">
        <h2 className="section-title">{t("modelOps.detail.title")}</h2>
        <p className="status-text">{detail.error || t("modelOps.detail.notFound")}</p>
      </section>
    );
  }

  const model = detail.model;

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="modelops-card-header">
          <div className="card-stack">
            <h2 className="section-title">{model.name}</h2>
            <p className="status-text">{model.id}</p>
          </div>
          <div className="button-row">
            {canTest && (
              <Link className="btn btn-primary" to={`/control/models/${encodeURIComponent(model.id)}/test`}>
                {t("modelOps.actions.testModel")}
              </Link>
            )}
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

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.detail.metadataTitle")}</h2>
        <ul className="card-stack" aria-label="Model metadata">
          <li className="status-row"><span>{`${t("modelOps.fields.providerModelId")}: ${model.provider_model_id ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.source")}: ${model.source ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.localPath")}: ${model.artifact?.storage_path ?? model.metadata?.local_path ?? "--"}`}</span></li>
          <li className="status-row"><span>{`${t("modelOps.fields.comment")}: ${model.comment ?? "--"}`}</span></li>
        </ul>
      </article>

      <UsageSummaryPanel usage={detail.usage} />
      <ValidationHistoryPanel validations={detail.validations} />

      {detail.feedback && <p className="status-text">{detail.feedback}</p>}
      {detail.error && <p className="error-text">{detail.error}</p>}
    </section>
  );
}
