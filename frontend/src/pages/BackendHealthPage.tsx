import { useState } from "react";
import { useTranslation } from "react-i18next";

type LoadState = "idle" | "loading" | "success" | "error";
type ServiceStatus = "up" | "down" | "unknown";

type ServiceRow = {
  service: string;
  container: string;
  target: string;
  status: ServiceStatus;
};

type SystemHealthResponse = {
  status: string;
  services: Array<{
    service: string;
    container: string;
    target: string;
    reachable: boolean;
  }>;
};

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";
const initialServices: ServiceRow[] = [
  { service: "Frontend", container: "frontend", target: "http://frontend:3000", status: "unknown" },
  { service: "Backend", container: "backend", target: "http://backend:5000", status: "unknown" },
  { service: "LLM API", container: "llm", target: "http://llm:8000", status: "unknown" },
  { service: "LLM Runtime", container: "llm_runtime", target: "http://llm_runtime:8000", status: "unknown" },
  { service: "Agent Engine", container: "agent_engine", target: "http://agent_engine:7000", status: "unknown" },
  { service: "Sandbox", container: "sandbox", target: "http://sandbox:6000", status: "unknown" },
  { service: "KWS", container: "kws", target: "http://kws:10400", status: "unknown" },
  { service: "Weaviate", container: "weaviate", target: "http://weaviate:8080", status: "unknown" },
  { service: "PostgreSQL", container: "postgres", target: "postgresql", status: "unknown" },
];

export default function BackendHealthPage(): JSX.Element {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [services, setServices] = useState<ServiceRow[]>(initialServices);
  const [errorMessage, setErrorMessage] = useState("");
  const [warningMessage, setWarningMessage] = useState("");

  const checkAllServices = async (): Promise<void> => {
    setState("loading");
    setErrorMessage("");
    setWarningMessage("");

    try {
      const response = await fetch(`${backendBaseUrl.replace(/\/$/, "")}/system/health`, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (response.status === 404) {
        const [backendResponse, voiceResponse] = await Promise.all([
          fetch(`${backendBaseUrl.replace(/\/$/, "")}/health`, {
            method: "GET",
            headers: { Accept: "application/json" },
          }),
          fetch(`${backendBaseUrl.replace(/\/$/, "")}/voice/health`, {
            method: "GET",
            headers: { Accept: "application/json" },
          }).catch(() => null),
        ]);

        const backendUp = backendResponse.ok;
        let kwsUp = false;
        if (voiceResponse?.ok) {
          const voicePayload = (await voiceResponse.json()) as {
            voice?: { kws?: { reachable?: boolean } };
          };
          kwsUp = Boolean(voicePayload.voice?.kws?.reachable);
        }

        setServices((currentServices) => currentServices.map((service) => {
          if (service.container === "backend") {
            return { ...service, status: backendUp ? "up" : "down" };
          }
          if (service.container === "kws") {
            return { ...service, status: kwsUp ? "up" : "down" };
          }
          return { ...service, status: "unknown" };
        }));

        setWarningMessage(t("backend.error.legacyFallback"));
        setState("success");
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as SystemHealthResponse;
      setServices(payload.services.map((service) => ({
        service: service.service,
        container: service.container,
        target: service.target,
        status: service.reachable ? "up" : "down",
      })));
      setState("success");
    } catch (error) {
      setServices((currentServices) => currentServices.map((service) => ({ ...service, status: "unknown" })));
      setErrorMessage(error instanceof Error ? error.message : "Unknown error");
      setState("error");
    }
  };

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("backend.sectionTitle")}</h2>

      <div className="status-row">
        <span className="field-label">{t("backend.status.label")}</span>
        <strong className="status-pill" data-state={state}>{t(`backend.state.${state}`)}</strong>
      </div>

      <button type="button" className="btn btn-primary" onClick={checkAllServices} disabled={state === "loading"}>
        {state === "loading" ? t("backend.check.loadingAll") : t("backend.check.ctaAll")}
      </button>

      <div className="health-table-wrap">
        <table className="health-table">
          <thead>
            <tr>
              <th>{t("backend.table.service")}</th>
              <th>{t("backend.table.container")}</th>
              <th>{t("backend.table.target")}</th>
              <th>{t("backend.table.status")}</th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.container}>
                <td>{service.service}</td>
                <td><code className="code-inline">{service.container}</code></td>
                <td>{service.target}</td>
                <td>
                  <span className={`health-icon health-icon-${service.status}`} aria-hidden="true" />
                  <span className="health-label">{t(`backend.serviceStatus.${service.status}`)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {state === "error" && (
        <p className="status-text error-text">{`${t("backend.error.prefix")} ${errorMessage}`}</p>
      )}
      {warningMessage && (
        <p className="status-text">{warningMessage}</p>
      )}
    </section>
  );
}
