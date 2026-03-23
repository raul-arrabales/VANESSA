import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";
import PlatformDeploymentAuditTable from "../features/platform-control/components/PlatformDeploymentAuditTable";
import PlatformDeploymentsDirectory from "../features/platform-control/components/PlatformDeploymentsDirectory";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import { usePlatformOverview } from "../features/platform-control/hooks/usePlatformOverview";
import { useAuth } from "../auth/AuthProvider";

function readLocationFeedback(state: unknown): string {
  if (state && typeof state === "object" && "feedbackMessage" in state && typeof state.feedbackMessage === "string") {
    return state.feedbackMessage;
  }
  return "";
}

export default function PlatformDeploymentsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const location = useLocation();
  const { errorMessage, capabilities, deployments, activationAudit } = usePlatformOverview(token);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");

  const filteredDeployments = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return deployments.filter((deployment) => {
      const matchesSearch = normalizedSearch.length === 0
        || deployment.display_name.toLowerCase().includes(normalizedSearch)
        || deployment.slug.toLowerCase().includes(normalizedSearch)
        || deployment.description.toLowerCase().includes(normalizedSearch);
      const matchesActive = activeFilter === "all"
        || (activeFilter === "active" ? deployment.is_active : !deployment.is_active);
      return matchesSearch && matchesActive;
    });
  }, [activeFilter, deployments, search]);

  return (
    <PlatformPageLayout
      title={t("platformControl.deployments.title")}
      description={t("platformControl.deployments.pageDescription")}
      errorMessage={errorMessage}
      feedbackMessage={readLocationFeedback(location.state)}
      actions={(
        <Link className="btn btn-primary" to="/control/platform/deployments/new">
          {t("platformControl.actions.createDeployment")}
        </Link>
      )}
    >
      <article className="panel card-stack">
        <div className="platform-filter-grid">
          <label className="card-stack">
            <span className="field-label">{t("platformControl.filters.search")}</span>
            <input className="field-input" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("platformControl.filters.state")}</span>
            <select className="field-input" value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)}>
              <option value="all">{t("platformControl.filters.all")}</option>
              <option value="active">{t("platformControl.badges.active")}</option>
              <option value="inactive">{t("platformControl.badges.inactive")}</option>
            </select>
          </label>
        </div>
      </article>

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.deployments")}</h3>
          <p className="status-text">{t("platformControl.deployments.directoryDescription", { count: filteredDeployments.length })}</p>
        </div>
        <PlatformDeploymentsDirectory deployments={filteredDeployments} capabilities={capabilities} />
      </article>

      <PlatformDeploymentAuditTable entries={activationAudit} />
    </PlatformPageLayout>
  );
}
