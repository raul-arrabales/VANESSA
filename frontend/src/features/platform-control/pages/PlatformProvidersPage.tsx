import { useTranslation } from "react-i18next";
import { useLocation, useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import { useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import PlatformPageLayout from "../components/PlatformPageLayout";
import PlatformProviderCreatePanel from "../components/PlatformProviderCreatePanel";
import PlatformProvidersDirectory from "../components/PlatformProvidersDirectory";
import { type ProviderEnabledFilter, usePlatformProvidersDirectoryFilters } from "../hooks/usePlatformProvidersDirectoryFilters";
import { usePlatformProvidersData } from "../hooks/usePlatformProvidersData";
import { PROVIDER_ORIGIN_OPTIONS, type ProviderOriginSelection } from "../providerForm";

type PlatformProvidersView = "providers" | "create";

const PLATFORM_PROVIDERS_VIEW_ORDER: ReadonlyArray<PlatformProvidersView> = [
  "providers",
  "create",
];

function resolvePlatformProvidersView(value: string | null): PlatformProvidersView {
  if (value === "providers" || value === "create") {
    return value;
  }
  return "providers";
}

function resolveProviderOriginFilter(value: string): ProviderOriginSelection {
  return value === "local" || value === "cloud" ? value : "";
}

function resolveEnabledFilter(value: string): ProviderEnabledFilter {
  return value === "enabled" || value === "disabled" ? value : "all";
}

export default function PlatformProvidersPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { errorMessage, providers, providerFamilies, deployments } = usePlatformProvidersData(token);
  useRouteActionFeedback(location.state);
  const {
    search,
    setSearch,
    capabilityFilter,
    setCapabilityFilter,
    providerKeyFilter,
    setProviderKeyFilter,
    providerOriginFilter,
    setProviderOriginFilter,
    enabledFilter,
    setEnabledFilter,
    filteredProviders,
    capabilities,
    providerKeys,
  } = usePlatformProvidersDirectoryFilters({
    providers,
    providerFamilies,
  });
  const activeView = resolvePlatformProvidersView(searchParams.get("view"));
  const submenuItems = PLATFORM_PROVIDERS_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`platformControl.providers.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

  function handleChangeView(view: PlatformProvidersView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  return (
    <PlatformPageLayout
      title={t("platformControl.providers.title")}
      description={t("platformControl.providers.pageDescription")}
      errorMessage={errorMessage}
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("platformControl.providers.views.aria")} />}
    >
      {activeView === "providers" ? (
        <>
          <article className="panel card-stack">
            <div className="platform-filter-grid">
              <label className="card-stack">
                <span className="field-label">{t("platformControl.filters.search")}</span>
                <input className="field-input" value={search} onChange={(event) => setSearch(event.target.value)} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.filters.capability")}</span>
                <select className="field-input" value={capabilityFilter} onChange={(event) => setCapabilityFilter(event.target.value)}>
                  <option value="">{t("platformControl.filters.all")}</option>
                  {capabilities.map((capability) => (
                    <option key={capability} value={capability}>
                      {capability}
                    </option>
                  ))}
                </select>
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.filters.providerFamily")}</span>
                <select className="field-input" value={providerKeyFilter} onChange={(event) => setProviderKeyFilter(event.target.value)}>
                  <option value="">{t("platformControl.filters.all")}</option>
                  {providerKeys.map((providerKey) => (
                    <option key={providerKey} value={providerKey}>
                      {providerKey}
                    </option>
                  ))}
                </select>
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.filters.providerOrigin")}</span>
                <select
                  className="field-input"
                  value={providerOriginFilter}
                  onChange={(event) => setProviderOriginFilter(resolveProviderOriginFilter(event.target.value))}
                >
                  <option value="">{t("platformControl.filters.all")}</option>
                  {PROVIDER_ORIGIN_OPTIONS.map((origin) => (
                    <option key={origin.value} value={origin.value}>
                      {t(origin.labelKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.filters.state")}</span>
                <select className="field-input" value={enabledFilter} onChange={(event) => setEnabledFilter(resolveEnabledFilter(event.target.value))}>
                  <option value="all">{t("platformControl.filters.all")}</option>
                  <option value="enabled">{t("platformControl.badges.enabled")}</option>
                  <option value="disabled">{t("platformControl.badges.disabled")}</option>
                </select>
              </label>
            </div>
          </article>

          <article className="panel card-stack">
            <div className="status-row">
              <h3 className="section-title">{t("platformControl.sections.providers")}</h3>
              <p className="status-text">{t("platformControl.providers.directoryDescription", { count: filteredProviders.length })}</p>
            </div>
            <PlatformProvidersDirectory
              providers={filteredProviders}
              providerFamilies={providerFamilies}
              deployments={deployments}
            />
          </article>
        </>
      ) : null}

      {activeView === "create" ? <PlatformProviderCreatePanel /> : null}
    </PlatformPageLayout>
  );
}
