import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import { useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import PlatformPageLayout from "../components/PlatformPageLayout";
import PlatformProviderCreatePanel from "../components/PlatformProviderCreatePanel";
import PlatformProvidersDirectory from "../components/PlatformProvidersDirectory";
import { usePlatformProvidersData } from "../hooks/usePlatformProvidersData";

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

export default function PlatformProvidersPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { errorMessage, providers, providerFamilies, deployments } = usePlatformProvidersData(token);
  useRouteActionFeedback(location.state);
  const [search, setSearch] = useState("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [providerKeyFilter, setProviderKeyFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState("all");
  const activeView = resolvePlatformProvidersView(searchParams.get("view"));
  const submenuItems = PLATFORM_PROVIDERS_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`platformControl.providers.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

  const filteredProviders = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return providers.filter((provider) => {
      const matchesSearch = normalizedSearch.length === 0
        || provider.display_name.toLowerCase().includes(normalizedSearch)
        || provider.slug.toLowerCase().includes(normalizedSearch)
        || provider.provider_key.toLowerCase().includes(normalizedSearch)
        || provider.endpoint_url.toLowerCase().includes(normalizedSearch);
      const matchesCapability = !capabilityFilter || provider.capability === capabilityFilter;
      const matchesProviderKey = !providerKeyFilter || provider.provider_key === providerKeyFilter;
      const matchesEnabled = enabledFilter === "all"
        || (enabledFilter === "enabled" ? provider.enabled : !provider.enabled);
      return matchesSearch && matchesCapability && matchesProviderKey && matchesEnabled;
    });
  }, [capabilityFilter, enabledFilter, providerKeyFilter, providers, search]);

  const capabilities = Array.from(new Set(providers.map((provider) => provider.capability)));
  const providerKeys = Array.from(new Set(providerFamilies.map((family) => family.provider_key)));

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
                <span className="field-label">{t("platformControl.filters.state")}</span>
                <select className="field-input" value={enabledFilter} onChange={(event) => setEnabledFilter(event.target.value)}>
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
