import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { OptionCardItem } from "../components/OptionCardGrid";
import OptionCardGrid from "../components/OptionCardGrid";
import PlatformCapabilitiesOverview from "../features/platform-control/components/PlatformCapabilitiesOverview";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import PlatformSummaryCards from "../features/platform-control/components/PlatformSummaryCards";
import { usePlatformOverview } from "../features/platform-control/hooks/usePlatformOverview";
import { getActiveDeployment } from "../features/platform-control/utils";
import { useAuth } from "../auth/AuthProvider";

export default function PlatformControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { state, errorMessage, capabilities, deployments, activationAudit, reload } = usePlatformOverview(token);

  const activeDeployment = getActiveDeployment(deployments);
  const latestActivation = activationAudit[0] ?? null;
  const requiredCapabilities = capabilities.filter((capability) => capability.required);
  const coveredRequiredCapabilities = requiredCapabilities.filter((capability) => capability.active_provider !== null);

  const entryCards = useMemo((): OptionCardItem[] => [
    {
      id: "providers",
      title: t("platformControl.home.providersTitle"),
      description: t("platformControl.home.providersDescription"),
      to: "/control/platform/providers",
      icon: "adminPage",
    },
    {
      id: "deployments",
      title: t("platformControl.home.deploymentsTitle"),
      description: t("platformControl.home.deploymentsDescription"),
      to: "/control/platform/deployments",
      icon: "models",
    },
  ], [t]);

  return (
    <PlatformPageLayout
      title={t("platformControl.title")}
      description={t("platformControl.home.description")}
      errorMessage={errorMessage}
    >
      <article className="panel card-stack">
        <PlatformSummaryCards
          state={state}
          activeDeployment={activeDeployment}
          latestActivation={latestActivation}
          coveredRequiredCapabilities={coveredRequiredCapabilities.length}
          requiredCapabilities={requiredCapabilities.length}
        />
      </article>

      <PlatformCapabilitiesOverview
        capabilities={capabilities}
        activeDeployment={activeDeployment}
        isRefreshing={state === "loading"}
        onRefresh={() => void reload()}
      />

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.home.exploreTitle")}</h3>
          <p className="status-text">{t("platformControl.home.exploreDescription")}</p>
        </div>
        <OptionCardGrid items={entryCards} ariaLabel={t("platformControl.home.exploreAria")} />
      </article>
    </PlatformPageLayout>
  );
}
