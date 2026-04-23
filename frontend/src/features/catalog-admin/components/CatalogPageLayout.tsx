import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import TabbedWorkspaceLayout from "../../../components/TabbedWorkspaceLayout";
import { buildCatalogControlUrl, CATALOG_CONTROL_NAV_ITEMS, type CatalogControlSection } from "../routes";

type CatalogPageLayoutProps = {
  activeSection: CatalogControlSection;
  title: string;
  description: string;
  actions?: ReactNode;
  secondaryNavigation?: ReactNode;
  errorMessage?: string;
  children: ReactNode;
};

export default function CatalogPageLayout({
  activeSection,
  title,
  description,
  actions,
  secondaryNavigation,
  errorMessage,
  children,
}: CatalogPageLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const tabs = CATALOG_CONTROL_NAV_ITEMS.map((item) => ({
    id: item.id,
    label: t(item.labelKey),
    to: buildCatalogControlUrl(item.id),
    isActive: activeSection === item.id,
  }));

  return (
    <TabbedWorkspaceLayout
      eyebrow={t("catalogControl.eyebrow")}
      title={title}
      description={description}
      tabs={tabs}
      ariaLabel={t("catalogControl.navigation.aria")}
      actions={actions}
      secondaryNavigation={secondaryNavigation}
    >
      {errorMessage ? <p className="status-text error-text">{errorMessage}</p> : null}
      {children}
    </TabbedWorkspaceLayout>
  );
}
