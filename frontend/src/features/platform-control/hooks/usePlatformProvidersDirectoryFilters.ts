import { useMemo, useState } from "react";
import type { PlatformProvider, PlatformProviderFamily } from "../../../api/platform";
import type { ProviderOriginSelection } from "../providerForm";

type UsePlatformProvidersDirectoryFiltersOptions = {
  providers: PlatformProvider[];
  providerFamilies: PlatformProviderFamily[];
};

export type ProviderEnabledFilter = "all" | "enabled" | "disabled";

export function usePlatformProvidersDirectoryFilters({
  providers,
  providerFamilies,
}: UsePlatformProvidersDirectoryFiltersOptions) {
  const [search, setSearch] = useState("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [providerKeyFilter, setProviderKeyFilter] = useState("");
  const [providerOriginFilter, setProviderOriginFilter] = useState<ProviderOriginSelection>("");
  const [enabledFilter, setEnabledFilter] = useState<ProviderEnabledFilter>("all");

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
      const matchesProviderOrigin = !providerOriginFilter || provider.provider_origin === providerOriginFilter;
      const matchesEnabled = enabledFilter === "all"
        || (enabledFilter === "enabled" ? provider.enabled : !provider.enabled);
      return matchesSearch && matchesCapability && matchesProviderKey && matchesProviderOrigin && matchesEnabled;
    });
  }, [capabilityFilter, enabledFilter, providerKeyFilter, providerOriginFilter, providers, search]);

  const capabilities = useMemo(
    () => Array.from(new Set(providers.map((provider) => provider.capability))),
    [providers],
  );
  const providerKeys = useMemo(
    () => Array.from(new Set(providerFamilies.map((family) => family.provider_key))),
    [providerFamilies],
  );

  return {
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
  };
}
