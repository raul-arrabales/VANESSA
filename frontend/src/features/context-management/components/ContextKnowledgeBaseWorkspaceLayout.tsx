import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router-dom";
import type { KnowledgeBase } from "../../../api/context";
import {
  buildKnowledgeBaseWorkspacePath,
  CONTEXT_KNOWLEDGE_BASE_WORKSPACE_NAV_ITEMS,
} from "../routes";

type ContextKnowledgeBaseWorkspaceLayoutProps = {
  knowledgeBase: KnowledgeBase | null;
  children: ReactNode;
};

export function ContextKnowledgeBaseWorkspaceLayout({
  knowledgeBase,
  children,
}: ContextKnowledgeBaseWorkspaceLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const { knowledgeBaseId = "" } = useParams();
  const location = useLocation();

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="platform-page-header">
          <div className="status-row">
            <p className="eyebrow">{t("contextManagement.eyebrow")}</p>
            <h2 className="section-title">{knowledgeBase?.display_name ?? t("contextManagement.detailTitle")}</h2>
            <p className="status-text">{knowledgeBase?.description || t("contextManagement.detailDescription")}</p>
          </div>
          <div className="platform-page-actions">
            <Link className="btn btn-secondary" to="/control/context">
              {t("contextManagement.actions.back")}
            </Link>
          </div>
        </div>
        <nav className="platform-subnav" aria-label={t("contextManagement.navigation.aria")}>
          {CONTEXT_KNOWLEDGE_BASE_WORKSPACE_NAV_ITEMS.map((item) => {
            const itemPath = buildKnowledgeBaseWorkspacePath(knowledgeBaseId, item.section);
            const isActive = item.section === "overview"
              ? location.pathname === itemPath
              : location.pathname === itemPath || location.pathname.startsWith(`${itemPath}/`);
            return (
              <Link key={item.section} className="link-chip" data-active={isActive ? "true" : "false"} to={itemPath}>
                {t(item.labelKey)}
              </Link>
            );
          })}
        </nav>
      </article>

      {children}
    </section>
  );
}
