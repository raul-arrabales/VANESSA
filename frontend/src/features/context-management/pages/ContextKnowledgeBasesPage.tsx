import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useContextKnowledgeBaseList } from "../hooks/useContextKnowledgeBaseList";

export default function ContextKnowledgeBasesPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { knowledgeBases, errorMessage, loading, isSuperadmin } = useContextKnowledgeBaseList();

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
                    <div className="platform-inline-meta">
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
                    <Link className="btn btn-secondary" to={`/control/context/${knowledgeBase.id}`}>
                      {t("contextManagement.actions.manage")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
