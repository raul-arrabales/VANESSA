import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import { useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import PlatformDeploymentAuditTable from "../components/PlatformDeploymentAuditTable";
import PlatformDeploymentCreatePanel from "../components/PlatformDeploymentCreatePanel";
import PlatformDeploymentsDirectory from "../components/PlatformDeploymentsDirectory";
import PlatformPageLayout from "../components/PlatformPageLayout";
import { usePlatformOverview } from "../hooks/usePlatformOverview";

type PlatformDeploymentsView = "profiles" | "history" | "create";

const PLATFORM_DEPLOYMENTS_VIEW_ORDER: ReadonlyArray<PlatformDeploymentsView> = [
  "profiles",
  "history",
  "create",
];

function resolvePlatformDeploymentsView(value: string | null): PlatformDeploymentsView {
  if (value === "profiles" || value === "history" || value === "create") {
    return value;
  }
  return "profiles";
}

export default function PlatformDeploymentsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { errorMessage, capabilities, deployments, activationAudit } = usePlatformOverview(token);
  useRouteActionFeedback(location.state);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const activeView = resolvePlatformDeploymentsView(searchParams.get("view"));
  const submenuItems = PLATFORM_DEPLOYMENTS_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`platformControl.deployments.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

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

  function handleChangeView(view: PlatformDeploymentsView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  return (
    <PlatformPageLayout
      title={t("platformControl.deployments.title")}
      description={t("platformControl.deployments.pageDescription")}
      errorMessage={errorMessage}
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("platformControl.deployments.views.aria")} />}
    >
      {activeView === "profiles" ? (
        <>
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
        </>
      ) : null}

      {activeView === "history" ? <PlatformDeploymentAuditTable entries={activationAudit} /> : null}
      {activeView === "create" ? <PlatformDeploymentCreatePanel /> : null}
    </PlatformPageLayout>
  );
}
