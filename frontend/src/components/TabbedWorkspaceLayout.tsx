import type { ReactNode } from "react";
import PageSectionTabs from "./PageSectionTabs";
import type { PageSectionTabItem } from "./navigation";

type TabbedWorkspaceLayoutProps = {
  eyebrow: string;
  title: string;
  description: string;
  tabs: PageSectionTabItem[];
  ariaLabel: string;
  actions?: ReactNode;
  secondaryNavigation?: ReactNode;
  children: ReactNode;
};

export default function TabbedWorkspaceLayout({
  eyebrow,
  title,
  description,
  tabs,
  ariaLabel,
  actions,
  secondaryNavigation,
  children,
}: TabbedWorkspaceLayoutProps): JSX.Element {
  return (
    <section className="card-stack tabbed-workspace-layout">
      <article className="panel card-stack tabbed-workspace-header-panel">
        <div className="platform-page-header">
          <div className="status-row">
            <p className="eyebrow">{eyebrow}</p>
            <h2 className="section-title">{title}</h2>
            <p className="status-text">{description}</p>
          </div>
          {actions ? <div className="platform-page-actions">{actions}</div> : null}
        </div>
        <PageSectionTabs items={tabs} ariaLabel={ariaLabel} />
        {secondaryNavigation ? (
          <div className="tabbed-workspace-secondary-nav">
            {secondaryNavigation}
          </div>
        ) : null}
      </article>

      {children}
    </section>
  );
}
