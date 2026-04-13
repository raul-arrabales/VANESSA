import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { ModelCredential } from "../../../api/modelops/types";
import { CLOUD_PROVIDER_OPTIONS } from "../domain";

type CloudCredentialListProps = {
  credentials: ModelCredential[];
  isLoading: boolean;
  isRevoking: boolean;
  onRevoke: (credentialId: string) => Promise<void>;
};

export default function CloudCredentialList({
  credentials,
  isLoading,
  isRevoking,
  onRevoke,
}: CloudCredentialListProps): JSX.Element {
  const { t } = useTranslation("common");
  const [credentialToRevoke, setCredentialToRevoke] = useState<ModelCredential | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  const getProviderLabel = (provider: string): string => {
    const option = CLOUD_PROVIDER_OPTIONS.find((candidate) => candidate.value === provider);
    return option ? t(option.labelKey) : provider;
  };

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.cloud.savedCredentialsTitle")}</h2>
      {isLoading ? <p className="status-text">{t("modelOps.states.loading")}</p> : null}
      {!isLoading && credentials.length === 0 ? (
        <p className="status-text">{t("modelOps.cloud.emptyCredentials")}</p>
      ) : null}
      {!isLoading && credentials.length > 0 ? (
        <ul className="card-stack" aria-label={t("modelOps.cloud.savedCredentialsListAria")}>
          {credentials.map((credential) => (
            <li key={credential.id} className="panel panel-nested card-stack">
              <div className="modelops-card-header">
                <strong>{credential.display_name}</strong>
                <div className="button-row">
                  <span className="status-chip status-chip-neutral">{`****${credential.api_key_last4}`}</span>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => setCredentialToRevoke(credential)}
                  >
                    {t("modelOps.cloud.revokeCredential")}
                  </button>
                </div>
              </div>
              <div className="inline-meta-list">
                <span className="status-chip status-chip-info">{getProviderLabel(credential.provider)}</span>
                <span className="status-chip status-chip-neutral">
                  {credential.credential_scope === "platform"
                    ? t("modelOps.scopes.platform")
                    : t("modelOps.scopes.personal")}
                </span>
                {credential.api_base_url ? (
                  <span className="status-text">{credential.api_base_url}</span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {credentialToRevoke ? (
        <ModalDialog
          title={t("modelOps.cloud.revokeCredentialDialog.title")}
          description={t("modelOps.cloud.revokeCredentialDialog.description", {
            name: credentialToRevoke.display_name,
          })}
          onClose={() => setCredentialToRevoke(null)}
          closeDisabled={isRevoking}
          initialFocusRef={confirmButtonRef}
          actions={(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setCredentialToRevoke(null)}
                disabled={isRevoking}
              >
                {t("modelOps.cloud.revokeCredentialDialog.cancel")}
              </button>
              <button
                ref={confirmButtonRef}
                type="button"
                className="btn btn-danger"
                onClick={() => {
                  void onRevoke(credentialToRevoke.id).then(() => setCredentialToRevoke(null));
                }}
                disabled={isRevoking}
              >
                {t("modelOps.cloud.revokeCredentialDialog.confirm")}
              </button>
            </>
          )}
        />
      ) : null}
    </article>
  );
}
