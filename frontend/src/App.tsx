import { useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
};

type LoadState = "idle" | "loading" | "success" | "error";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() ||
  "http://backend:5000";

export default function App(): JSX.Element {
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
    <main className="page">
      <section className="panel">
        <h1>VANESSA</h1>
        <p className="subtitle">Dummy frontend bootstrap</p>

        <div className="status-row">
          <span className="label">Backend URL</span>
          <code>{healthUrl}</code>
        </div>

        <div className="status-row">
          <span className="label">Backend status</span>
          <strong data-state={state}>{state.toUpperCase()}</strong>
        </div>

        <button type="button" onClick={checkBackend} disabled={state === "loading"}>
          {state === "loading" ? "Checking..." : "Check backend"}
        </button>

        {state === "success" && result && (
          <pre>{JSON.stringify(result, null, 2)}</pre>
        )}

        {state === "error" && (
          <p className="error">Request failed: {errorMessage}</p>
        )}
      </section>
    </main>
  );
}
