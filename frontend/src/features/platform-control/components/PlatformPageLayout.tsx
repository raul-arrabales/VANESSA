import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

type PlatformPageLayoutProps = {
  title: string;
  description: string;
  actions?: ReactNode;
  errorMessage?: string;
  children: ReactNode;
};

const subnavItems = [
  { to: "/control/platform", labelKey: "platformControl.navigation.home" },
  { to: "/control/platform/providers", labelKey: "platformControl.navigation.providers" },
  { to: "/control/platform/deployments", labelKey: "platformControl.navigation.deployments" },
];

export default function PlatformPageLayout({
  title,
  description,
  actions,
  errorMessage,
  children,
}: PlatformPageLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const location = useLocation();

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
        <nav className="platform-subnav" aria-label={t("platformControl.navigation.aria")}>
          {subnavItems.map((item) => {
            const isActive = item.to === "/control/platform"
              ? location.pathname === item.to
              : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
            return (
              <Link key={item.to} className="link-chip" data-active={isActive ? "true" : "false"} to={item.to}>
                {t(item.labelKey)}
              </Link>
            );
          })}
        </nav>
      </article>

      {errorMessage ? <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${errorMessage}`}</p> : null}

      {children}
    </section>
  );
}
