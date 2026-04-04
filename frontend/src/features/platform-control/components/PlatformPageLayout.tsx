import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import PageSectionTabs from "../../../components/PageSectionTabs";
import { PLATFORM_PAGE_NAV_ITEMS } from "../routes";

type PlatformPageLayoutProps = {
  title: string;
  description: string;
  actions?: ReactNode;
  errorMessage?: string;
  children: ReactNode;
};

export default function PlatformPageLayout({
  title,
  description,
  actions,
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
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="platform-page-header">
          <div className="status-row">
            <p className="eyebrow">{t("platformControl.eyebrow")}</p>
            <h2 className="section-title">{title}</h2>
            <p className="status-text">{description}</p>
          </div>
          {actions ? <div className="platform-page-actions">{actions}</div> : null}
        </div>
        <PageSectionTabs items={tabItems} ariaLabel={t("platformControl.navigation.aria")} />
      </article>

      {errorMessage ? <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${errorMessage}`}</p> : null}

      {children}
    </section>
  );
}
