import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { initI18n } from "./i18n";
import "./styles.css";
import { AuthProvider } from "./auth/AuthProvider";
import { RuntimeModeProvider } from "./runtime/RuntimeModeProvider";
import { ThemeProvider } from "./theme/ThemeProvider";
import { ActionFeedbackProvider } from "./feedback/ActionFeedbackProvider";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element #root was not found");
}

const root = ReactDOM.createRoot(rootElement);

function renderStartupError(): void {
  root.render(
    <React.StrictMode>
      <div className="page-shell">
        <main className="panel" role="main">
          <p className="eyebrow">VANESSA</p>
          <h1 className="section-title">Unable to load application translations.</h1>
          <p className="status-text">Reload the page and try again.</p>
        </main>
      </div>
    </React.StrictMode>,
  );
}

function renderApp(): void {
  root.render(
    <React.StrictMode>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <RuntimeModeProvider>
              <ActionFeedbackProvider>
                <App />
              </ActionFeedbackProvider>
            </RuntimeModeProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </React.StrictMode>,
  );
}

async function bootstrap(): Promise<void> {
  try {
    await initI18n();
    renderApp();
  } catch (error) {
    console.error("[i18n] failed to initialize application translations", error);
    renderStartupError();
  }
}

void bootstrap();
