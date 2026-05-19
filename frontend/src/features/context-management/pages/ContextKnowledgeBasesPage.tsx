import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase } from "../../../api/context";
import ActionIcon from "../../../components/ActionIcon";
import IconButton from "../../../components/IconButton";
import { deriveLifecycleCounts, LifecycleGraph, LifecycleGraphModal } from "../../../components/LifecycleGraph";
import {
  createKnowledgeBaseLifecycleGraphDefinition,
  getKnowledgeBaseLifecycleState,
  getKnowledgeBaseLifecycleSummary,
} from "../knowledgeBaseLifecycleGraph";
import { useContextKnowledgeBaseList } from "../hooks/useContextKnowledgeBaseList";

export default function ContextKnowledgeBasesPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { knowledgeBases, errorMessage, loading, isSuperadmin } = useContextKnowledgeBaseList();
  const [lifecycleKnowledgeBase, setLifecycleKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const lifecycleDefinition = useMemo(() => createKnowledgeBaseLifecycleGraphDefinition(t), [t]);
  const lifecycleCounts = useMemo(
    () => deriveLifecycleCounts(knowledgeBases, lifecycleDefinition, getKnowledgeBaseLifecycleState),
    [knowledgeBases, lifecycleDefinition],
  );

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h2 className="section-title">{t("contextManagement.title")}</h2>
          <p className="status-text">{t("contextManagement.description")}</p>
        </div>
        {isSuperadmin ? (
          <Link className="btn btn-primary" to="/control/context/new">
            {t("contextManagement.actions.newKnowledgeBase")}
          </Link>
        ) : null}
      </div>

      {errorMessage ? <p className="status-text error-text">{errorMessage}</p> : null}
      {loading ? <p className="status-text">{t("contextManagement.states.loading")}</p> : null}
      {!loading && knowledgeBases.length === 0 ? <p className="status-text">{t("contextManagement.states.empty")}</p> : null}

      {knowledgeBases.length > 0 ? (
        <article className="panel panel-nested card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h3 className="section-title">{t("contextManagement.lifecycle.title")}</h3>
              <p className="status-text">{t("contextManagement.lifecycle.summaryDescription")}</p>
            </div>
          </div>
          <LifecycleGraph
            definition={lifecycleDefinition}
            counts={lifecycleCounts}
            currentLabel={t("contextManagement.lifecycle.currentState")}
            unknownLabel={t("platformControl.summary.unknown")}
          />
        </article>
      ) : null}

      {knowledgeBases.length > 0 ? (
        <div className="health-table-wrap">
          <table className="health-table" aria-label={t("contextManagement.aria.table")}>
            <thead>
              <tr>
                <th>{t("contextManagement.columns.name")}</th>
                <th>{t("contextManagement.columns.index")}</th>
                <th>{t("contextManagement.columns.status")}</th>
                <th>{t("contextManagement.columns.documents")}</th>
                <th>{t("contextManagement.columns.bindings")}</th>
                <th>{t("contextManagement.columns.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {knowledgeBases.map((knowledgeBase) => (
                <tr key={knowledgeBase.id}>
                  <td>
                    <strong>{knowledgeBase.display_name}</strong>
                    <div className="inline-meta-list">
                      <span className="status-text">{knowledgeBase.slug}</span>
                    </div>
                  </td>
                  <td>{knowledgeBase.index_name}</td>
                  <td>
                    <span className="platform-badge" data-tone={knowledgeBase.sync_status === "ready" ? "enabled" : "disabled"}>
                      {`${knowledgeBase.lifecycle_state} / ${knowledgeBase.sync_status}`}
                    </span>
                  </td>
                  <td>{knowledgeBase.document_count}</td>
                  <td>{knowledgeBase.binding_count ?? 0}</td>
                  <td>
                    <div className="compact-registry-actions">
                      <IconButton
                        label={t("contextManagement.lifecycle.actionLabel", { name: knowledgeBase.display_name })}
                        onClick={() => setLifecycleKnowledgeBase(knowledgeBase)}
                      >
                        <ActionIcon name="lifecycle" />
                      </IconButton>
                      <Link className="btn btn-secondary" to={`/control/context/${knowledgeBase.id}`}>
                        {t("contextManagement.actions.manage")}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {lifecycleKnowledgeBase ? (
        <LifecycleGraphModal
          title={t("contextManagement.lifecycle.modalTitle", { name: lifecycleKnowledgeBase.display_name })}
          description={t("contextManagement.lifecycle.modalDescription")}
          definition={lifecycleDefinition}
          currentState={getKnowledgeBaseLifecycleState(lifecycleKnowledgeBase)}
          supportingText={getKnowledgeBaseLifecycleSummary(t, lifecycleKnowledgeBase)}
          currentLabel={t("contextManagement.lifecycle.currentState")}
          unknownLabel={t("platformControl.summary.unknown")}
          closeLabel={t("contextManagement.actions.cancel")}
          onClose={() => setLifecycleKnowledgeBase(null)}
        />
      ) : null}
    </section>
  );
}
