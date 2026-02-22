import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./components/LanguageSwitcher";
import ThemeToggle from "./components/ThemeToggle";

type HealthResponse = {
  status: string;
  service: string;
};

type LoadState = "idle" | "loading" | "success" | "error";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() ||
  "/api";

function AppHeader(): JSX.Element {
  const { t } = useTranslation("common");
  return (
    <header className="app-header panel">
      <div>
        <p className="eyebrow">{t("app.eyebrow")}</p>
        <h1 className="app-title">{t("app.title")}</h1>
        <p className="subtitle">{t("app.subtitle")}</p>
      </div>
      <div className="toolbar" role="group" aria-label={t("app.controls") }>
        <nav className="nav-links" aria-label={t("nav.aria")}>
          <a href="/" className="link-chip">{t("nav.home")}</a>
          <a href="/style-guide" className="link-chip">{t("nav.styleGuide")}</a>
        </nav>
        <ThemeToggle />
        <LanguageSwitcher />
      </div>
    </header>
  );
}

function HomeView(): JSX.Element {
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

const colorTokens = [
  "--bg-canvas",
  "--bg-surface",
  "--bg-subtle",
  "--text-primary",
  "--text-secondary",
  "--accent-primary",
  "--accent-secondary",
  "--border-muted",
  "--status-success",
  "--status-error",
  "--lcars-rail",
] as const;

const spacingTokens = ["--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6"] as const;
const radiusTokens = ["--radius-sm", "--radius-md", "--radius-lg"] as const;
const shadowTokens = ["--shadow-1", "--shadow-2", "--shadow-3"] as const;

function StyleGuideView(): JSX.Element {
  return (
    <section className="style-guide card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">Color Tokens</h2>
        <p className="status-text">Semantic roles only. Components should never hardcode hex values.</p>
        <div className="token-grid">
          {colorTokens.map((token) => (
            <div key={token} className="token-card">
              <div className="token-swatch" style={{ backgroundColor: `var(${token})` }} aria-hidden="true" />
              <code className="code-inline">{token}</code>
            </div>
          ))}
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Typography</h2>
        <p className="type-specimen heading">Heading specimen: NCC-1701 mission control</p>
        <p className="type-specimen body">Body specimen: human-readable operational copy optimized for long sessions.</p>
        <p className="type-specimen mono"><code className="code-inline">Monospace specimen: await engine.health()</code></p>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Spacing / Radius / Shadow</h2>
        <div className="token-row">
          {spacingTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
        <div className="token-row">
          {radiusTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
        <div className="token-row">
          {shadowTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Primitives</h2>
        <div className="button-row">
          <button className="btn btn-primary" type="button">Primary</button>
          <button className="btn btn-secondary" type="button">Secondary</button>
          <button className="btn btn-ghost" type="button">Ghost</button>
          <button className="btn btn-primary" type="button" disabled>Disabled</button>
        </div>

        <div className="form-grid">
          <label className="control-group">
            <span className="field-label">Input</span>
            <input className="field-input" placeholder="Search logs" />
          </label>
          <label className="control-group">
            <span className="field-label">Select</span>
            <select className="field-input" defaultValue="active">
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </label>
          <label className="control-group">
            <span className="field-label">Textarea</span>
            <textarea className="field-input" rows={3} placeholder="Operator notes" />
          </label>
        </div>

        <div className="status-demo">
          <span className="status-pill" data-state="success">SUCCESS</span>
          <span className="status-pill" data-state="error">ERROR</span>
        </div>
      </article>
    </section>
  );
}

export default function App(): JSX.Element {
  const isStyleGuide = window.location.pathname === "/style-guide";

  return (
    <main className="page-shell">
      <AppHeader />
      {isStyleGuide ? <StyleGuideView /> : <HomeView />}
    </main>
  );
}
