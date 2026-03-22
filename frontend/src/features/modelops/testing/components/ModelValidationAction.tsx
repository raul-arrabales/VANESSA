import { useState } from "react";
import { useTranslation } from "react-i18next";

type ModelValidationActionProps = {
  canValidate: boolean;
  latestSuccessfulTestRunId: string;
  isPending: boolean;
  onValidate: () => Promise<void>;
};

export default function ModelValidationAction({
  canValidate,
  latestSuccessfulTestRunId,
  isPending,
  onValidate,
}: ModelValidationActionProps): JSX.Element {
  const { t } = useTranslation("common");
  const [isConfirming, setIsConfirming] = useState(false);
  const isDisabled = !canValidate || !latestSuccessfulTestRunId || isPending;

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.testing.validationActionTitle")}</h2>
      <p className="status-text">
        {latestSuccessfulTestRunId
          ? t("modelOps.testing.validationReady")
          : t("modelOps.testing.validationBlocked")}
      </p>
      {!isConfirming ? (
        <button
          type="button"
          className="btn btn-primary"
          disabled={isDisabled}
          onClick={() => setIsConfirming(true)}
        >
          {t("modelOps.actions.markValidated")}
        </button>
      ) : (
        <div className="button-row">
          <button
            type="button"
            className="btn btn-primary"
            disabled={isPending}
            onClick={() => {
              void onValidate().finally(() => setIsConfirming(false));
            }}
          >
            {t("modelOps.actions.confirmValidation")}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isPending}
            onClick={() => setIsConfirming(false)}
          >
            {t("modelOps.actions.cancel")}
          </button>
        </div>
      )}
    </article>
  );
}
