import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BackendHealthPage from "./BackendHealthPage";

const fetchServiceLogServicesMock = vi.fn();
const fetchServiceLogSnapshotMock = vi.fn();
const streamServiceLogsMock = vi.fn();
const useAuthMock = vi.fn(() => ({ token: "token" }));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock("../api/serviceLogs", () => ({
  fetchServiceLogServices: (...args: unknown[]) => fetchServiceLogServicesMock(...args),
  fetchServiceLogSnapshot: (...args: unknown[]) => fetchServiceLogSnapshotMock(...args),
  streamServiceLogs: (...args: unknown[]) => streamServiceLogsMock(...args),
}));

const translate = (key: string, values?: Record<string, string | number>) => {
  if (key === "backend.architecture.meta") {
    return `Nodes: ${values?.nodes} | Edges: ${values?.edges} | Generated: ${values?.generatedAt}`;
  }
  if (key === "backend.logs.description") {
    return `Inspect recent and live log output for ${values?.service}.`;
  }
  if (key === "backend.logs.resultsTitle") {
    return `${values?.count} log entries`;
  }
  if (key === "backend.logs.tailHint") {
    return `Showing the current in-memory tail of ${values?.count} entries.`;
  }
  if (key === "backend.logs.errors.unknownService") {
    return `The service "${values?.service}" is not available in this local staging stack.`;
  }
  const dictionary: Record<string, string> = {
    "backend.sectionTitle": "System Health",
    "backend.status.label": "Backend status",
    "backend.state.idle": "IDLE",
    "backend.state.loading": "LOADING",
    "backend.state.success": "SUCCESS",
    "backend.state.error": "ERROR",
    "backend.check.ctaAll": "Check all services",
    "backend.check.loadingAll": "Checking all services...",
    "backend.architecture.title": "Architecture Diagram",
    "backend.architecture.aria": "System architecture diagram",
    "backend.architecture.unavailable": "Architecture diagram is unavailable in this backend environment.",
    "backend.error.architectureUnavailable": "Architecture artifacts could not be loaded.",
    "backend.error.prefix": "Request failed:",
    "backend.table.service": "Service",
    "backend.table.container": "Container",
    "backend.table.target": "Health target",
    "backend.table.status": "Status",
    "backend.table.actions": "Actions",
    "backend.serviceStatus.up": "Up",
    "backend.serviceStatus.down": "Down",
    "backend.serviceStatus.unknown": "Unknown",
    "backend.logs.openAction": "Open logs",
    "backend.logs.title": "Service Logs",
    "backend.logs.descriptionGeneric": "Inspect recent and live log output for a VANESSA service.",
    "backend.logs.backToOverview": "Back to system health",
    "backend.logs.serviceLabel": "Selected service",
    "backend.logs.containerLabel": "Container",
    "backend.logs.serviceStatusLabel": "Current status",
    "backend.logs.liveFollow": "Follow live",
    "backend.logs.missingServiceTitle": "Select a service",
    "backend.logs.resultsTitle": "log entries",
    "backend.logs.loading": "Loading service logs...",
    "backend.logs.empty": "No log entries matched the current filters.",
    "backend.logs.tableAria": "Service log entries",
    "backend.logs.table.timestamp": "Timestamp",
    "backend.logs.table.level": "Level",
    "backend.logs.table.eventType": "Event type",
    "backend.logs.table.message": "Message",
    "backend.logs.filters.startTime": "Start time",
    "backend.logs.filters.endTime": "End time",
    "backend.logs.filters.level": "Level",
    "backend.logs.filters.eventType": "Event type",
    "backend.logs.filters.search": "Search",
    "backend.logs.filters.searchPlaceholder": "Filter log lines",
    "backend.logs.filters.allLevels": "All levels",
    "backend.logs.filters.allEventTypes": "All event types",
    "backend.logs.level.error": "Error",
    "backend.logs.level.warning": "Warning",
    "backend.logs.level.info": "Info",
    "backend.logs.level.debug": "Debug",
    "backend.logs.level.unknown": "Unknown",
    "backend.logs.eventType.generic": "Generic",
    "backend.logs.eventType.health": "Health",
    "backend.logs.eventType.http": "HTTP",
    "backend.logs.eventType.startup": "Startup",
    "backend.logs.stream.label": "Stream status",
    "backend.logs.stream.idle": "Idle",
    "backend.logs.stream.connecting": "Connecting",
    "backend.logs.stream.live": "Live",
    "backend.logs.stream.disconnected": "Disconnected",
    "backend.logs.stream.disconnectedMessage": "Live follow stopped. The current tail remains available.",
    "backend.logs.errors.missingService": "Choose a service from System Health to inspect its logs.",
    "backend.logs.errors.loadFailed": "Service logs could not be loaded.",
  };
  return dictionary[key] ?? key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: translate,
  }),
}));

function renderPage(route = "/control/system-health"): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/control/system-health" element={<BackendHealthPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BackendHealthPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    fetchServiceLogServicesMock.mockReset();
    fetchServiceLogSnapshotMock.mockReset();
    streamServiceLogsMock.mockReset();
    useAuthMock.mockReturnValue({ token: "token" });
  });

  it("loads architecture artifacts, maps status to nodes, and exposes open-logs actions", async () => {
    const openMock = vi.spyOn(window, "open").mockImplementation(() => null);

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/system/health")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "ok",
            services: [
              { service: "Backend", container: "backend", target: "http://backend:5000", reachable: true },
              { service: "Image Analysis", container: "image_analysis", target: "http://image_analysis:8090", reachable: true },
              { service: "KWS", container: "kws", target: "http://kws:10400", reachable: false },
            ],
          }),
        };
      }
      if (url.endsWith("/system/architecture")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            version: "1.0",
            generated_at: "2026-01-01T00:00:00+00:00",
            nodes: [
              { id: "backend", container: "backend", label: "Backend", group: "api", description: "Backend" },
              { id: "image_analysis", container: "image_analysis", label: "Image Analysis", group: "runtime", description: "Image Analysis" },
              { id: "kws", container: "kws", label: "KWS", group: "api", description: "KWS" },
            ],
            edges: [{ id: "kws-backend", from: "kws", to: "backend", protocol: "HTTP", purpose: "Wake", kind: "event", direction: "outbound" }],
          }),
        };
      }
      if (url.endsWith("/system/architecture.svg")) {
        return {
          ok: true,
          status: 200,
          text: async () => [
            "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\">",
            "<g id=\"node-backend\" data-container=\"backend\"><rect x=\"1\" y=\"1\" width=\"10\" height=\"10\"/></g>",
            "<g id=\"node-image_analysis\" data-container=\"image_analysis\"><rect x=\"10\" y=\"10\" width=\"10\" height=\"10\"/></g>",
            "<g id=\"node-kws\" data-container=\"kws\"><rect x=\"20\" y=\"20\" width=\"10\" height=\"10\"/></g>",
            "</svg>",
          ].join(""),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Check all services" }));

    await screen.findByText("Nodes: 3 | Edges: 1 | Generated: 2026-01-01T00:00:00+00:00");

    await waitFor(() => {
      expect(container.querySelector('[data-container="backend"]')?.getAttribute("data-status")).toBe("up");
      expect(container.querySelector('[data-container="image_analysis"]')?.getAttribute("data-status")).toBe("up");
      expect(container.querySelector('[data-container="kws"]')?.getAttribute("data-status")).toBe("down");
    });

    await userEvent.click(screen.getAllByRole("button", { name: "Open logs" })[0]);
    expect(openMock).toHaveBeenCalledWith("/control/system-health?view=logs&service=backend", "_blank", "noopener,noreferrer");
  });

  it("renders the logs subview, appends streamed events, and filters entries", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/system/health")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "ok",
            services: [{ service: "Backend", container: "backend", target: "http://backend:5000", reachable: true }],
          }),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    fetchServiceLogServicesMock.mockResolvedValue([{ id: "backend", display_name: "Backend" }]);
    fetchServiceLogSnapshotMock.mockResolvedValue({
      service: "backend",
      display_name: "Backend",
      tail: 200,
      entries: [
        {
          id: "entry-1",
          service: "backend",
          timestamp: "2026-05-25T10:00:00Z",
          level: "error",
          event_type: "http",
          raw: "2026-05-25T10:00:00Z [ERROR] GET /health failed",
          message: "[ERROR] GET /health failed",
        },
      ],
    });
    streamServiceLogsMock.mockImplementation(async (_token, _service, options) => {
      options.onEvent?.({
        id: "entry-2",
        service: "backend",
        timestamp: "2026-05-25T10:01:00Z",
        level: "info",
        event_type: "startup",
        raw: "2026-05-25T10:01:00Z Started backend",
        message: "Started backend",
      });
    });

    renderPage("/control/system-health?view=logs&service=backend");

    await screen.findByRole("heading", { name: "Service Logs" });
    await screen.findByText("Inspect recent and live log output for Backend.");
    await screen.findByText("Started backend");
    expect(screen.getByText("Disconnected")).toBeVisible();

    await userEvent.selectOptions(screen.getByLabelText("Level"), "error");
    expect(screen.getByText("[ERROR] GET /health failed")).toBeVisible();
    expect(screen.queryByText("Started backend")).toBeNull();
  });

  it("shows a clear error state for invalid log-view service ids", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok", services: [] }),
    })));
    fetchServiceLogServicesMock.mockResolvedValue([{ id: "backend", display_name: "Backend" }]);

    renderPage("/control/system-health?view=logs&service=unknown");

    await screen.findByText('The service "unknown" is not available in this local staging stack.');
  });

  it("marks the frontend as up from the active browser session", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/system/health")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "degraded",
            services: [
              { service: "Frontend", container: "frontend", target: "http://frontend:3000", reachable: false },
              { service: "Backend", container: "backend", target: "http://backend:5000", reachable: true },
            ],
          }),
        };
      }
      if (url.endsWith("/system/architecture")) {
        return { ok: false, status: 503 };
      }
      if (url.endsWith("/system/architecture.svg")) {
        return { ok: false, status: 503 };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Check all services" }));

    await screen.findByText(window.location.origin);
    const frontendRow = screen.getByText("Frontend").closest("tr");
    expect(frontendRow).not.toBeNull();
    expect(within(frontendRow as HTMLTableRowElement).getByText("Up")).toBeInTheDocument();
  });
});
