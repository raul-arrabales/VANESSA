import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

type HealthResponse = {
  status: string;
  service: string;
};

type LoadState = "idle" | "loading" | "success" | "error";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() ||
  "/api";

export default function BackendHealthPage(): JSX.Element {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [result, setResult] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const healthUrl = useMemo(() => `${backendBaseUrl.replace(/\/$/, "")}/health`, []);

  const checkBackend = async (): Promise<void> => {
    setState("loading");
    setResult(null);
    setErrorMessage("");

    try {
      const response = await fetch(healthUrl, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as HealthResponse;
      setResult(payload);
      setState("success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setErrorMessage(message);
      setState("error");
    }
  };

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("backend.sectionTitle")}</h2>

      <div className="status-row">
        <span className="field-label">{t("backend.url.label")}</span>
        <code className="code-inline">{healthUrl}</code>
      </div>

      <div className="status-row">
        <span className="field-label">{t("backend.status.label")}</span>
        <strong className="status-pill" data-state={state}>{t(`backend.state.${state}`)}</strong>
      </div>

      <button type="button" className="btn btn-primary" onClick={checkBackend} disabled={state === "loading"}>
        {state === "loading" ? t("backend.check.loading") : t("backend.check.cta")}
      </button>

      {state === "success" && result && (
        <pre className="code-block">{JSON.stringify(result, null, 2)}</pre>
      )}

      {state === "error" && (
        <p className="status-text error-text">{`${t("backend.error.prefix")} ${errorMessage}`}</p>
      )}
    </section>
  );
}
