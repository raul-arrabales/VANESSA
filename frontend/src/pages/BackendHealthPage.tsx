import { useEffect, useRef, useState } from "react";
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

type ArchitectureGraphResponse = {
  version: string;
  generated_at: string;
  nodes: Array<{
    id: string;
    container: string;
    label: string;
    group: string;
    description: string;
  }>;
  edges: Array<{
    id: string;
    from: string;
    to: string;
    protocol: string;
    purpose: string;
    kind: string;
    direction: string;
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

function mapServicesFromHealth(payload: SystemHealthResponse): ServiceRow[] {
  return payload.services.map((service) => ({
    service: service.service,
    container: service.container,
    target: service.target,
    status: service.reachable ? "up" : "down",
  }));
}

export default function BackendHealthPage(): JSX.Element {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [services, setServices] = useState<ServiceRow[]>(initialServices);
  const [architectureGraph, setArchitectureGraph] = useState<ArchitectureGraphResponse | null>(null);
  const [architectureSvg, setArchitectureSvg] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [warningMessage, setWarningMessage] = useState("");
  const architectureContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!architectureContainerRef.current || !architectureSvg) {
      return;
    }

    const statusByContainer = new Map<string, ServiceStatus>(
      services.map((service) => [service.container, service.status]),
    );

    const nodes = architectureContainerRef.current.querySelectorAll<SVGGElement>("[data-container]");
    nodes.forEach((node) => {
      const container = node.getAttribute("data-container");
      if (!container) {
        return;
      }
      node.setAttribute("data-status", statusByContainer.get(container) ?? "unknown");
    });
  }, [architectureSvg, services]);

  const checkAllServices = async (): Promise<void> => {
    setState("loading");
    setErrorMessage("");
    setWarningMessage("");

    const warnings: string[] = [];

    try {
      const apiBase = backendBaseUrl.replace(/\/$/, "");
      const [healthResponse, architectureJsonResponse, architectureSvgResponse] = await Promise.all([
        fetch(`${apiBase}/system/health`, {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }),
        fetch(`${apiBase}/system/architecture`, {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }).catch(() => null),
        fetch(`${apiBase}/system/architecture.svg`, {
          method: "GET",
          headers: {
            Accept: "image/svg+xml",
          },
        }).catch(() => null),
      ]);

      if (architectureJsonResponse?.ok) {
        const architectureJson = (await architectureJsonResponse.json()) as ArchitectureGraphResponse;
        setArchitectureGraph(architectureJson);
      } else {
        setArchitectureGraph(null);
        warnings.push(t("backend.error.architectureUnavailable"));
      }

      if (architectureSvgResponse?.ok) {
        setArchitectureSvg(await architectureSvgResponse.text());
      } else {
        setArchitectureSvg("");
      }

      if (healthResponse.status === 404) {
        const [backendResponse, voiceResponse] = await Promise.all([
          fetch(`${apiBase}/health`, {
            method: "GET",
            headers: { Accept: "application/json" },
          }),
          fetch(`${apiBase}/voice/health`, {
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

        warnings.push(t("backend.error.legacyFallback"));
        setWarningMessage(warnings.join(" "));
        setState("success");
        return;
      }

      if (!healthResponse.ok) {
        throw new Error(`HTTP ${healthResponse.status}`);
      }

      const payload = (await healthResponse.json()) as SystemHealthResponse;
      setServices(mapServicesFromHealth(payload));
      if (warnings.length > 0) {
        setWarningMessage(warnings.join(" "));
      }
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

      <article className="architecture-panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("backend.architecture.title")}</h3>
          {architectureGraph && (
            <span className="status-text">
              {t("backend.architecture.meta", {
                nodes: architectureGraph.nodes.length,
                edges: architectureGraph.edges.length,
                generatedAt: architectureGraph.generated_at,
              })}
            </span>
          )}
        </div>

        {architectureSvg ? (
          <div
            ref={architectureContainerRef}
            className="architecture-diagram"
            aria-label={t("backend.architecture.aria")}
            dangerouslySetInnerHTML={{ __html: architectureSvg }}
          />
        ) : (
          <p className="status-text">{t("backend.architecture.unavailable")}</p>
        )}
      </article>

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
