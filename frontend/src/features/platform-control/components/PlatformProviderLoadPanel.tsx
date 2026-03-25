import { useTranslation } from "react-i18next";
import {
  type ProviderLoadDisplayData,
  type ProviderLoadPanelPhase,
  isTerminalProviderLoadPhase,
} from "../providerLoad";

type PlatformProviderLoadPanelProps = {
  providerDisplayName: string;
  loadPanelPhase: ProviderLoadPanelPhase;
  display: ProviderLoadDisplayData;
  onDismiss: () => void;
};

export default function PlatformProviderLoadPanel({
  providerDisplayName,
  loadPanelPhase,
  display,
  onDismiss,
}: PlatformProviderLoadPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <aside
      className="provider-load-panel panel"
      role="status"
      aria-live="polite"
      aria-label={t("platformControl.providers.loadPanelTitle")}
    >
      <div className="provider-load-panel-header">
        <div className="card-stack">
          <p className="eyebrow">{t("platformControl.providers.loadPanelTitle")}</p>
          <h3 className="section-title">{providerDisplayName}</h3>
        </div>
        <span
          className="status-pill"
          data-state={loadPanelPhase === "loaded" ? "success" : loadPanelPhase === "error" ? "error" : "loading"}
        >
          {display.loadPanelPhaseLabel}
        </span>
      </div>
      <p className="modal-message">{display.loadPanelSummary}</p>
      <div className="platform-detail-grid">
        <div className="platform-summary-card">
          <span className="field-label">{t("platformControl.providers.loadPanelRequestedModelLabel")}</span>
          <strong>{display.loadPanelModelName}</strong>
          <span className="status-text">{display.loadPanelModelId}</span>
        </div>
        <div className="platform-summary-card">
          <span className="field-label">{t("platformControl.providers.loadPanelRuntimeLabel")}</span>
          <strong>{display.loadPanelRuntimeLabel}</strong>
          <span className={display.hasLoadError ? "status-text error-text" : "status-text"}>
            {display.loadStateHelperText}
          </span>
        </div>
      </div>
      <div
        className="provider-load-progress"
        data-phase={loadPanelPhase}
        role="progressbar"
        aria-valuetext={display.loadPanelPhaseLabel}
      >
        <div className="provider-load-progress-bar" />
      </div>
      <ul className="provider-load-timeline">
        {display.loadTimelineItems.map((item) => (
          <li key={item.label} className="provider-load-timeline-item" data-state={item.state}>
            <span className="provider-load-timeline-marker" aria-hidden="true" />
            <span className="status-text">{item.label}</span>
          </li>
        ))}
      </ul>
      {isTerminalProviderLoadPhase(loadPanelPhase) ? (
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onDismiss}>
            {t("platformControl.providers.loadPanelDismiss")}
          </button>
        </div>
      ) : null}
    </aside>
  );
}
