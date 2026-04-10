import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase } from "../../../api/context";
import { ContextKnowledgeBaseWorkspaceLayout } from "./ContextKnowledgeBaseWorkspaceLayout";

type ContextKnowledgeBaseWorkspaceFrameProps = {
  knowledgeBase: KnowledgeBase | null;
  loading: boolean;
  secondaryNavigation?: ReactNode;
  children: (knowledgeBase: KnowledgeBase) => ReactNode;
};

export function ContextKnowledgeBaseWorkspaceFrame({
  knowledgeBase,
  loading,
  secondaryNavigation,
  children,
}: ContextKnowledgeBaseWorkspaceFrameProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <ContextKnowledgeBaseWorkspaceLayout knowledgeBase={knowledgeBase} secondaryNavigation={secondaryNavigation}>
      {loading ? (
        <section className="panel">
          <p className="status-text">{t("contextManagement.states.loading")}</p>
        </section>
      ) : null}
      {knowledgeBase ? children(knowledgeBase) : null}
    </ContextKnowledgeBaseWorkspaceLayout>
  );
}
