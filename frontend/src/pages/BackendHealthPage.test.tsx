import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BackendHealthPage from "./BackendHealthPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, string | number>) => {
      if (key === "backend.architecture.meta") {
        return `Nodes: ${values?.nodes} | Edges: ${values?.edges} | Generated: ${values?.generatedAt}`;
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
        "backend.table.service": "Service",
        "backend.table.container": "Container",
        "backend.table.target": "Health target",
        "backend.table.status": "Status",
        "backend.serviceStatus.up": "Up",
        "backend.serviceStatus.down": "Down",
        "backend.serviceStatus.unknown": "Unknown",
      };
      return dictionary[key] ?? key;
    },
  }),
}));

describe("BackendHealthPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads architecture artifacts and maps service health status to diagram nodes", async () => {
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
            "<g id=\"node-kws\" data-container=\"kws\"><rect x=\"20\" y=\"20\" width=\"10\" height=\"10\"/></g>",
            "</svg>",
          ].join(""),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<BackendHealthPage />);
    await userEvent.click(screen.getByRole("button", { name: "Check all services" }));

    await screen.findByText("Nodes: 2 | Edges: 1 | Generated: 2026-01-01T00:00:00+00:00");

    await waitFor(() => {
      expect(container.querySelector('[data-container="backend"]')?.getAttribute("data-status")).toBe("up");
      expect(container.querySelector('[data-container="kws"]')?.getAttribute("data-status")).toBe("down");
    });
  });

  it("keeps service checks working when architecture artifacts are unavailable", async () => {
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

    render(<BackendHealthPage />);
    await userEvent.click(screen.getByRole("button", { name: "Check all services" }));

    await screen.findByText("Architecture diagram is unavailable in this backend environment.");
    await screen.findByText("Architecture artifacts could not be loaded.");
  });
});
