import { useTranslation } from "react-i18next";
import type { PlatformProviderValidation } from "../../../api/platform";
import type { ModelCredential } from "../../../api/modelops/types";

type PlatformProviderValidationPanelProps = {
  validation: PlatformProviderValidation | null;
  isValidating: boolean;
  credentials: ModelCredential[];
  credentialsLoading: boolean;
  selectedCredentialId: string;
  supportsByokValidation: boolean;
  onCredentialChange: (credentialId: string) => void;
  onValidate: () => void;
};

export default function PlatformProviderValidationPanel({
  validation,
  isValidating,
  credentials,
  credentialsLoading,
  selectedCredentialId,
  supportsByokValidation,
  onCredentialChange,
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

      {supportsByokValidation ? (
        <div className="card-stack">
          <label className="field-label" htmlFor="platform-provider-validation-credential">
            {t("platformControl.providers.validationCredentialLabel")}
          </label>
          <select
            id="platform-provider-validation-credential"
            className="field-input"
            value={selectedCredentialId}
            disabled={credentialsLoading}
            onChange={(event) => onCredentialChange(event.currentTarget.value)}
          >
            <option value="">{t("platformControl.providers.validationProviderSecrets")}</option>
            {credentials.map((credential) => (
              <option key={credential.id} value={credential.id}>
                {`${credential.display_name} · ${credential.provider} · ****${credential.api_key_last4}`}
              </option>
            ))}
          </select>
          <span className="status-text">
            {credentialsLoading
              ? t("platformControl.providers.validationCredentialsLoading")
              : credentials.length
                ? t("platformControl.providers.validationCredentialHelp")
                : t("platformControl.providers.validationNoCredentials")}
          </span>
        </div>
      ) : null}

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
          {typeof validation.validation.resources_reachable === "boolean" ? (
            <span className="status-text">
              {validation.validation.resources_reachable
                ? t("platformControl.providers.resourcesReachable")
                : t("platformControl.providers.resourcesUnavailable")}
            </span>
          ) : null}
          {validation.validation.credential ? (
            <span className="status-text">
              {t("platformControl.providers.validationCredentialUsed", {
                name: validation.validation.credential.display_name,
              })}
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
          {(validation.validation.resource_errors ?? []).map((error, index) => (
            <span key={`${error.code}-${error.resource_id ?? index}`} className="status-text">
              {t(`platformControl.providers.bindingErrors.${error.code}`, {
                resourceId: error.resource_id ?? t("platformControl.summary.none"),
                providerResourceId: error.provider_resource_id ?? t("platformControl.summary.none"),
              })}
            </span>
          ))}
          {(validation.validation.resources ?? []).length ? (
            <div className="card-stack">
              {(validation.validation.resources ?? []).map((resource) => (
                <span key={resource.id} className="status-text">
                  {resource.display_name ?? resource.id}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="status-text">{t("platformControl.providers.notValidated")}</p>
      )}
    </article>
  );
}
