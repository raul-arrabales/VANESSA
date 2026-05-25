import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import type { ApiError } from "../auth/authApi";
import {
  fetchServiceLogServices,
  fetchServiceLogSnapshot,
  streamServiceLogs,
  type ServiceLogCatalogEntry,
  type ServiceLogEntry,
} from "../api/serviceLogs";

type LoadState = "idle" | "loading" | "success" | "error";
type ServiceStatus = "up" | "down" | "unknown";
type BackendHealthView = "overview" | "logs";
type StreamState = "idle" | "connecting" | "live" | "disconnected";
type LogSortOrder = "desc" | "asc";

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
  { service: "LLM Runtime Inference", container: "llm_runtime_inference", target: "http://llm_runtime_inference:8000", status: "unknown" },
  { service: "LLM Runtime Embeddings", container: "llm_runtime_embeddings", target: "http://llm_runtime_embeddings:8000", status: "unknown" },
  { service: "Agent Engine", container: "agent_engine", target: "http://agent_engine:7000", status: "unknown" },
  { service: "Sandbox", container: "sandbox", target: "http://sandbox:6000", status: "unknown" },
  { service: "Image Analysis", container: "image_analysis", target: "http://image_analysis:8090", status: "unknown" },
  { service: "KWS", container: "kws", target: "http://kws:10400", status: "unknown" },
  { service: "Weaviate", container: "weaviate", target: "http://weaviate:8080", status: "unknown" },
  { service: "PostgreSQL", container: "postgres", target: "postgresql", status: "unknown" },
];

function mapServicesFromHealth(payload: SystemHealthResponse): ServiceRow[] {
  const frontendTarget = window.location.origin;
  return payload.services.map((service) => ({
    service: service.service,
    container: service.container,
    target: service.container === "frontend" ? frontendTarget : service.target,
    status: service.container === "frontend" ? "up" : service.reachable ? "up" : "down",
  }));
}

function resolveBackendHealthView(value: string | null): BackendHealthView {
  return value === "logs" ? "logs" : "overview";
}

function buildLogsViewUrl(service: string): string {
  const params = new URLSearchParams({ view: "logs", service });
  return `/control/system-health?${params.toString()}`;
}

function appendUniqueEntries(current: ServiceLogEntry[], incoming: ServiceLogEntry): ServiceLogEntry[] {
  if (current.some((entry) => entry.id === incoming.id)) {
    return current;
  }
  return [...current, incoming];
}

function normalizeFilterDateTime(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatEventTimestamp(value: string | null): string {
  if (!value) {
    return "--";
  }
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}

function streamStateLabelKey(state: StreamState): string {
  return `backend.logs.stream.${state}`;
}

export default function BackendHealthPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, setState] = useState<LoadState>("idle");
  const [services, setServices] = useState<ServiceRow[]>(initialServices);
  const [architectureGraph, setArchitectureGraph] = useState<ArchitectureGraphResponse | null>(null);
  const [architectureSvg, setArchitectureSvg] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [warningMessage, setWarningMessage] = useState("");
  const [logState, setLogState] = useState<LoadState>("idle");
  const [logEntries, setLogEntries] = useState<ServiceLogEntry[]>([]);
  const [logErrorMessage, setLogErrorMessage] = useState("");
  const [logServiceCatalog, setLogServiceCatalog] = useState<ServiceLogCatalogEntry[]>([]);
  const [streamState, setStreamState] = useState<StreamState>("idle");
  const [streamMessage, setStreamMessage] = useState("");
  const [streamSince, setStreamSince] = useState<string | undefined>(undefined);
  const [liveFollow, setLiveFollow] = useState(true);
  const [startTimeFilter, setStartTimeFilter] = useState("");
  const [endTimeFilter, setEndTimeFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [sortOrder, setSortOrder] = useState<LogSortOrder>("desc");
  const architectureContainerRef = useRef<HTMLDivElement | null>(null);

  const activeView = resolveBackendHealthView(searchParams.get("view"));
  const requestedService = searchParams.get("service")?.trim() || "";
  const selectedService = services.find((service) => service.container === requestedService) ?? null;
  const selectedCatalogService = logServiceCatalog.find((service) => service.id === requestedService) ?? null;

  const availableEventTypes = useMemo(() => {
    return Array.from(new Set(logEntries.map((entry) => entry.event_type))).sort();
  }, [logEntries]);

  const filteredLogEntries = useMemo(() => {
    const searchTerm = searchFilter.trim().toLowerCase();
    const startTimeMs = normalizeFilterDateTime(startTimeFilter);
    const endTimeMs = normalizeFilterDateTime(endTimeFilter);

    const filteredEntries = logEntries.filter((entry) => {
      if (levelFilter && entry.level !== levelFilter) {
        return false;
      }
      if (eventTypeFilter && entry.event_type !== eventTypeFilter) {
        return false;
      }
      if (searchTerm && !entry.raw.toLowerCase().includes(searchTerm) && !entry.message.toLowerCase().includes(searchTerm)) {
        return false;
      }
      const entryTimestampMs = entry.timestamp ? Date.parse(entry.timestamp) : Number.NaN;
      if (startTimeMs !== null && !Number.isNaN(entryTimestampMs) && entryTimestampMs < startTimeMs) {
        return false;
      }
      if (endTimeMs !== null && !Number.isNaN(entryTimestampMs) && entryTimestampMs > endTimeMs) {
        return false;
      }
      if ((startTimeMs !== null || endTimeMs !== null) && Number.isNaN(entryTimestampMs)) {
        return false;
      }
      return true;
    });

    return filteredEntries.slice().sort((left, right) => {
      const leftTime = left.timestamp ? Date.parse(left.timestamp) : Number.NaN;
      const rightTime = right.timestamp ? Date.parse(right.timestamp) : Number.NaN;
      if (!Number.isNaN(leftTime) && !Number.isNaN(rightTime) && leftTime !== rightTime) {
        return sortOrder === "desc" ? rightTime - leftTime : leftTime - rightTime;
      }
      if (!Number.isNaN(leftTime) && Number.isNaN(rightTime)) {
        return -1;
      }
      if (Number.isNaN(leftTime) && !Number.isNaN(rightTime)) {
        return 1;
      }
      return sortOrder === "desc"
        ? right.raw.localeCompare(left.raw)
        : left.raw.localeCompare(right.raw);
    });
  }, [endTimeFilter, eventTypeFilter, levelFilter, logEntries, searchFilter, sortOrder, startTimeFilter]);

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

  useEffect(() => {
    if (activeView !== "logs" || !token) {
      return;
    }

    let cancelled = false;

    const loadLogs = async (): Promise<void> => {
      setLogState("loading");
      setLogErrorMessage("");
      setStreamState("idle");
      setStreamMessage("");
      setLogEntries([]);

      try {
        const catalog = await fetchServiceLogServices(token);
        if (cancelled) {
          return;
        }
        setLogServiceCatalog(catalog);

        if (!requestedService) {
          setLogErrorMessage(t("backend.logs.errors.missingService"));
          setLogState("error");
          return;
        }

        if (!catalog.some((entry) => entry.id === requestedService)) {
          setLogErrorMessage(t("backend.logs.errors.unknownService", { service: requestedService }));
          setLogState("error");
          return;
        }

        const [snapshot, healthResponse] = await Promise.all([
          fetchServiceLogSnapshot(token, requestedService, { tail: 200 }),
          fetchSystemHealthStatusOnly(),
        ]);
        if (cancelled) {
          return;
        }

        if (healthResponse) {
          setServices(mapServicesFromHealth(healthResponse));
        }
        setLogEntries(snapshot.entries);
        setStreamSince(snapshot.entries.length > 0 ? snapshot.entries[snapshot.entries.length - 1].timestamp ?? new Date().toISOString() : new Date().toISOString());
        setLogState("success");
      } catch (error) {
        if (cancelled) {
          return;
        }
        setLogErrorMessage(error instanceof Error ? error.message : t("backend.logs.errors.loadFailed"));
        setLogState("error");
      }
    };

    void loadLogs();

    return () => {
      cancelled = true;
    };
  }, [activeView, requestedService, t, token]);

  useEffect(() => {
    if (activeView !== "logs" || !token || !requestedService || !liveFollow || logState !== "success") {
      return;
    }

    const controller = new AbortController();
    let cancelled = false;
    setStreamState("connecting");
    setStreamMessage("");

    void streamServiceLogs(token, requestedService, {
      signal: controller.signal,
      since: streamSince,
      onEvent: (entry) => {
        if (cancelled) {
          return;
        }
        setStreamState("live");
        setLogEntries((current) => appendUniqueEntries(current, entry));
      },
      onError: (error: ApiError) => {
        if (cancelled) {
          return;
        }
        setStreamState("disconnected");
        setStreamMessage(error.message);
      },
    })
      .then(() => {
        if (cancelled || controller.signal.aborted) {
          return;
        }
        setStreamState("disconnected");
        setStreamMessage(t("backend.logs.stream.disconnectedMessage"));
      })
      .catch((error: Error) => {
        if (cancelled || controller.signal.aborted) {
          return;
        }
        setStreamState("disconnected");
        setStreamMessage(error.message);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activeView, liveFollow, logState, requestedService, streamSince, t, token]);

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
          if (service.container === "frontend") {
            return { ...service, target: window.location.origin, status: "up" };
          }
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

  function handleOpenLogs(service: ServiceRow): void {
    const targetUrl = buildLogsViewUrl(service.container);
    window.open(targetUrl, "_blank", "noopener,noreferrer");
  }

  function handleBackToOverview(): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.delete("view");
    nextSearchParams.delete("service");
    setSearchParams(nextSearchParams);
  }

  return activeView === "logs" ? (
    <section className="panel card-stack">
      <div className="status-row">
        <div className="card-stack">
          <h2 className="section-title">{t("backend.logs.title")}</h2>
          <p className="status-text">
            {selectedCatalogService
              ? t("backend.logs.description", { service: selectedCatalogService.display_name })
              : t("backend.logs.descriptionGeneric")}
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={handleBackToOverview}>
          {t("backend.logs.backToOverview")}
        </button>
      </div>

      <article className="architecture-panel card-stack">
        <div className="status-row">
          <div className="card-stack">
            <span className="field-label">{t("backend.logs.serviceLabel")}</span>
            <strong>{selectedCatalogService?.display_name ?? (requestedService || t("backend.logs.missingServiceTitle"))}</strong>
          </div>
          <div className="card-stack system-log-summary">
            <span className="field-label">{t("backend.logs.stream.label")}</span>
            <strong className="status-text">{t(streamStateLabelKey(streamState))}</strong>
          </div>
        </div>
        <div className="status-row system-log-summary-grid">
          <div>
            <span className="field-label">{t("backend.logs.containerLabel")}</span>
            <div><code className="code-inline">{requestedService || "--"}</code></div>
          </div>
          <div>
            <span className="field-label">{t("backend.logs.serviceStatusLabel")}</span>
            <div>{selectedService ? t(`backend.serviceStatus.${selectedService.status}`) : t("backend.serviceStatus.unknown")}</div>
          </div>
          <label className="system-log-follow-toggle">
            <input type="checkbox" checked={liveFollow} onChange={(event) => setLiveFollow(event.target.checked)} />
            <span>{t("backend.logs.liveFollow")}</span>
          </label>
        </div>
        {streamMessage ? <p className="status-text">{streamMessage}</p> : null}
      </article>

      <article className="panel panel-nested card-stack">
        <div className="system-log-filter-grid">
          <label className="card-stack">
            <span className="field-label">{t("backend.logs.filters.startTime")}</span>
            <input
              type="datetime-local"
              className="field-input"
              value={startTimeFilter}
              onChange={(event) => setStartTimeFilter(event.target.value)}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("backend.logs.filters.endTime")}</span>
            <input
              type="datetime-local"
              className="field-input"
              value={endTimeFilter}
              onChange={(event) => setEndTimeFilter(event.target.value)}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("backend.logs.filters.level")}</span>
            <select className="field-input" value={levelFilter} onChange={(event) => setLevelFilter(event.target.value)}>
              <option value="">{t("backend.logs.filters.allLevels")}</option>
              <option value="error">{t("backend.logs.level.error")}</option>
              <option value="warning">{t("backend.logs.level.warning")}</option>
              <option value="info">{t("backend.logs.level.info")}</option>
              <option value="debug">{t("backend.logs.level.debug")}</option>
              <option value="unknown">{t("backend.logs.level.unknown")}</option>
            </select>
          </label>
          <label className="card-stack">
            <span className="field-label">{t("backend.logs.filters.eventType")}</span>
            <select className="field-input" value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)}>
              <option value="">{t("backend.logs.filters.allEventTypes")}</option>
              {availableEventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {t(`backend.logs.eventType.${eventType}`, { defaultValue: eventType })}
                </option>
              ))}
            </select>
          </label>
          <label className="card-stack">
            <span className="field-label">{t("backend.logs.filters.sortOrder")}</span>
            <select className="field-input" value={sortOrder} onChange={(event) => setSortOrder(event.target.value as LogSortOrder)}>
              <option value="desc">{t("backend.logs.filters.newestFirst")}</option>
              <option value="asc">{t("backend.logs.filters.oldestFirst")}</option>
            </select>
          </label>
          <label className="card-stack system-log-search-field">
            <span className="field-label">{t("backend.logs.filters.search")}</span>
            <input
              className="field-input"
              placeholder={t("backend.logs.filters.searchPlaceholder")}
              value={searchFilter}
              onChange={(event) => setSearchFilter(event.target.value)}
            />
          </label>
        </div>
      </article>

      <article className="architecture-panel card-stack">
        <div className="status-row">
          <span className="field-label">{t("backend.logs.resultsTitle", { count: filteredLogEntries.length })}</span>
          <span className="status-text">{t("backend.logs.tailHint", { count: logEntries.length })}</span>
        </div>

        {logState === "loading" ? <p className="status-text">{t("backend.logs.loading")}</p> : null}
        {logState === "error" ? <p className="status-text error-text">{logErrorMessage}</p> : null}
        {logState === "success" && filteredLogEntries.length === 0 ? (
          <p className="status-text">{t("backend.logs.empty")}</p>
        ) : null}

        {filteredLogEntries.length > 0 ? (
          <div className="health-table-wrap">
            <table className="health-table system-log-table" aria-label={t("backend.logs.tableAria")}>
              <thead>
                <tr>
                  <th>{t("backend.logs.table.timestamp")}</th>
                  <th>{t("backend.logs.table.level")}</th>
                  <th>{t("backend.logs.table.eventType")}</th>
                  <th>{t("backend.logs.table.message")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogEntries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatEventTimestamp(entry.timestamp)}</td>
                    <td>
                      <span className="system-log-badge" data-kind="level" data-level={entry.level}>
                        {t(`backend.logs.level.${entry.level}`, { defaultValue: entry.level })}
                      </span>
                    </td>
                    <td>
                      <span className="system-log-badge" data-kind="event-type">
                        {t(`backend.logs.eventType.${entry.event_type}`, { defaultValue: entry.event_type })}
                      </span>
                    </td>
                    <td className="system-log-message-cell"><code>{entry.message}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </section>
  ) : (
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
              <th>{t("backend.table.actions")}</th>
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
                <td>
                  <button type="button" className="btn btn-secondary" onClick={() => handleOpenLogs(service)}>
                    {t("backend.logs.openAction")}
                  </button>
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

async function fetchSystemHealthStatusOnly(): Promise<SystemHealthResponse | null> {
  const apiBase = backendBaseUrl.replace(/\/$/, "");
  const response = await fetch(`${apiBase}/system/health`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  }).catch(() => null);

  if (!response?.ok) {
    return null;
  }

  return response.json() as Promise<SystemHealthResponse>;
}
