export const PLATFORM_PAGE_NAV_ITEMS: ReadonlyArray<{
  id: string;
  to: string;
  labelKey: string;
}> = [
  { id: "overview", to: "/control/platform", labelKey: "platformControl.navigation.home" },
  { id: "providers", to: "/control/platform/providers", labelKey: "platformControl.navigation.providers" },
  { id: "deployments", to: "/control/platform/deployments", labelKey: "platformControl.navigation.deployments" },
];
