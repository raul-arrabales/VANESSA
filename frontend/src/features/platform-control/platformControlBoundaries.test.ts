import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import platformControlPageSource from "../../pages/PlatformControlPage.tsx?raw";
import platformProvidersPageSource from "../../pages/PlatformProvidersPage.tsx?raw";
import platformProviderCreatePageSource from "../../pages/PlatformProviderCreatePage.tsx?raw";
import platformProviderDetailPageSource from "../../pages/PlatformProviderDetailPage.tsx?raw";
import platformDeploymentsPageSource from "../../pages/PlatformDeploymentsPage.tsx?raw";
import platformDeploymentCreatePageSource from "../../pages/PlatformDeploymentCreatePage.tsx?raw";
import platformDeploymentDetailPageSource from "../../pages/PlatformDeploymentDetailPage.tsx?raw";

describe("platform-control boundaries", () => {
  it("keeps routes pointed at feature-domain platform pages", () => {
    expect(routesSource).toContain("../features/platform-control/pages/PlatformControlPage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformProvidersPage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformProviderCreatePage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformProviderDetailPage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformDeploymentsPage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformDeploymentCreatePage");
    expect(routesSource).toContain("../features/platform-control/pages/PlatformDeploymentDetailPage");
    expect(routesSource).not.toContain("../pages/PlatformControlPage");
    expect(routesSource).not.toContain("../pages/PlatformProvidersPage");
    expect(routesSource).not.toContain("../pages/PlatformProviderCreatePage");
    expect(routesSource).not.toContain("../pages/PlatformProviderDetailPage");
    expect(routesSource).not.toContain("../pages/PlatformDeploymentsPage");
    expect(routesSource).not.toContain("../pages/PlatformDeploymentCreatePage");
    expect(routesSource).not.toContain("../pages/PlatformDeploymentDetailPage");
  });

  it("keeps legacy page files as thin feature wrappers", () => {
    const pageSources = [
      platformControlPageSource,
      platformProvidersPageSource,
      platformProviderCreatePageSource,
      platformProviderDetailPageSource,
      platformDeploymentsPageSource,
      platformDeploymentCreatePageSource,
      platformDeploymentDetailPageSource,
    ];

    for (const source of pageSources) {
      expect(source).toContain('export { default } from "../features/platform-control/pages/');
      expect(source).not.toContain("../api/platform");
      expect(source).not.toContain("useState");
      expect(source).not.toContain("useEffect");
    }
  });
});
