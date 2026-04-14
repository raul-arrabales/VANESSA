import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import TabbedWorkspaceLayout from "../../../components/TabbedWorkspaceLayout";
import { PLATFORM_PAGE_NAV_ITEMS } from "../routes";

type PlatformPageLayoutProps = {
  title: string;
  description: string;
  actions?: ReactNode;
  secondaryNavigation?: ReactNode;
  errorMessage?: string;
  children: ReactNode;
};

export default function PlatformPageLayout({
  title,
  description,
  actions,
  secondaryNavigation,
  errorMessage,
  children,
}: PlatformPageLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const location = useLocation();
  const tabItems = PLATFORM_PAGE_NAV_ITEMS.map((item) => ({
    id: item.id,
    label: t(item.labelKey),
    to: item.to,
    isActive: item.to === "/control/platform"
      ? location.pathname === item.to
      : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
  }));

  return (
    <TabbedWorkspaceLayout
      eyebrow={t("platformControl.eyebrow")}
      title={title}
      description={description}
      tabs={tabItems}
      ariaLabel={t("platformControl.navigation.aria")}
      actions={actions}
      secondaryNavigation={secondaryNavigation}
    >
      {errorMessage ? <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${errorMessage}`}</p> : null}
      {children}
    </TabbedWorkspaceLayout>
  );
}
