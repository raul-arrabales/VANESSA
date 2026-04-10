import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router-dom";
import TabbedWorkspaceLayout from "../../../components/TabbedWorkspaceLayout";
import type { KnowledgeBase } from "../../../api/context";
import {
  buildKnowledgeBaseWorkspacePath,
  CONTEXT_KNOWLEDGE_BASE_WORKSPACE_NAV_ITEMS,
} from "../routes";

type ContextKnowledgeBaseWorkspaceLayoutProps = {
  knowledgeBase: KnowledgeBase | null;
  secondaryNavigation?: ReactNode;
  children: ReactNode;
};

export function ContextKnowledgeBaseWorkspaceLayout({
  knowledgeBase,
  secondaryNavigation,
  children,
}: ContextKnowledgeBaseWorkspaceLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const { knowledgeBaseId = "" } = useParams();
  const location = useLocation();
  const sectionTabs = CONTEXT_KNOWLEDGE_BASE_WORKSPACE_NAV_ITEMS.map((item) => {
    const itemPath = buildKnowledgeBaseWorkspacePath(knowledgeBaseId, item.section);
    const isActive = item.section === "overview"
      ? location.pathname === itemPath
      : location.pathname === itemPath || location.pathname.startsWith(`${itemPath}/`);

    return {
      id: item.section,
      label: t(item.labelKey),
      to: itemPath,
      isActive,
    };
  });

  return (
    <TabbedWorkspaceLayout
      eyebrow={t("contextManagement.eyebrow")}
      title={knowledgeBase?.display_name ?? t("contextManagement.detailTitle")}
      description={knowledgeBase?.description || t("contextManagement.detailDescription")}
      tabs={sectionTabs}
      ariaLabel={t("contextManagement.navigation.aria")}
      actions={(
        <Link className="btn btn-secondary" to="/control/context">
          {t("contextManagement.actions.back")}
        </Link>
      )}
      secondaryNavigation={secondaryNavigation}
    >
      {children}
    </TabbedWorkspaceLayout>
  );
}
