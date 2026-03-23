import { useTranslation } from "react-i18next";
import type { PlatformProviderValidation } from "../../../api/platform";

type PlatformProviderValidationPanelProps = {
  validation: PlatformProviderValidation | null;
  isValidating: boolean;
  onValidate: () => void;
};

export default function PlatformProviderValidationPanel({
  validation,
  isValidating,
  onValidate,
}: PlatformProviderValidationPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="platform-section-header">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.validation")}</h3>
          <p className="status-text">{t("platformControl.providers.validationDescription")}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onValidate} disabled={isValidating}>
          {isValidating ? t("platformControl.actions.validating") : t("platformControl.actions.validate")}
        </button>
      </div>

      {validation ? (
        <div className="card-stack">
          <div className="status-row">
            <span className="platform-badge" data-tone={validation.validation.health.reachable ? "active" : "inactive"}>
              {validation.validation.health.reachable ? t("platformControl.badges.active") : t("platformControl.badges.inactive")}
            </span>
            <span className="status-text">
              {t("platformControl.providers.validationStatus", { code: validation.validation.health.status_code })}
            </span>
          </div>
          {typeof validation.validation.models_reachable === "boolean" ? (
            <span className="status-text">
              {validation.validation.models_reachable
                ? t("platformControl.providers.modelsReachable")
                : t("platformControl.providers.modelsUnavailable")}
            </span>
          ) : null}
          {typeof validation.validation.embeddings_reachable === "boolean" ? (
            <span className="status-text">
              {validation.validation.embeddings_reachable
                ? t("platformControl.providers.embeddingsReachable", {
                    dimension: validation.validation.embedding_dimension ?? 0,
                  })
                : t("platformControl.providers.embeddingsUnavailable")}
            </span>
          ) : null}
          {validation.validation.binding_error ? (
            <span className="status-text">
              {t(`platformControl.providers.bindingErrors.${validation.validation.binding_error}`)}
            </span>
          ) : null}
          {(validation.validation.served_model_errors ?? []).map((error, index) => (
            <span key={`${error.code}-${error.served_model_id ?? index}`} className="status-text">
              {t(`platformControl.providers.bindingErrors.${error.code}`, {
                modelId: error.served_model_id ?? t("platformControl.summary.none"),
                runtimeModelId: error.runtime_model_id ?? t("platformControl.summary.none"),
              })}
            </span>
          ))}
        </div>
      ) : (
        <p className="status-text">{t("platformControl.providers.notValidated")}</p>
      )}
    </article>
  );
}
