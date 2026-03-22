import { useTranslation } from "react-i18next";

type ModelTestDebugPanelProps = {
  requestPayload: unknown;
  responsePayload: unknown;
};

export default function ModelTestDebugPanel({
  requestPayload,
  responsePayload,
}: ModelTestDebugPanelProps): JSX.Element | null {
  const { t } = useTranslation("common");

  if (!requestPayload && !responsePayload) {
    return null;
  }

  return (
    <article className="panel card-stack">
      <details>
        <summary>{t("modelOps.testing.debugTitle")}</summary>
        <div className="card-stack">
          <pre className="status-text">{JSON.stringify(requestPayload ?? {}, null, 2)}</pre>
          <pre className="status-text">{JSON.stringify(responsePayload ?? {}, null, 2)}</pre>
        </div>
      </details>
    </article>
  );
}
