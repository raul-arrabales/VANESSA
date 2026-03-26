import { type FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  deleteKnowledgeBase,
  deleteKnowledgeBaseDocument,
  getKnowledgeBase,
  listKnowledgeBaseDocuments,
  queryKnowledgeBase,
  resyncKnowledgeBase,
  updateKnowledgeBase,
  createKnowledgeBaseDocument,
  updateKnowledgeBaseDocument,
  uploadKnowledgeBaseDocuments,
  type KnowledgeBase,
  type KnowledgeDocument,
  type KnowledgeBaseQueryResult,
} from "../api/context";
import { useAuth } from "../auth/AuthProvider";
import {
  useActionFeedback,
  useRouteActionFeedback,
  withActionFeedbackState,
} from "../feedback/ActionFeedbackProvider";

type DocumentFormState = {
  id: string | null;
  title: string;
  sourceName: string;
  uri: string;
  text: string;
};

const EMPTY_DOCUMENT_FORM: DocumentFormState = {
  id: null,
  title: "",
  sourceName: "",
  uri: "",
  text: "",
};

export default function ContextKnowledgeBaseDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { knowledgeBaseId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, user } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const isSuperadmin = user?.role === "superadmin";
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ slug: "", displayName: "", description: "", lifecycleState: "active" });
  const [documentForm, setDocumentForm] = useState<DocumentFormState>(EMPTY_DOCUMENT_FORM);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalTopK, setRetrievalTopK] = useState("5");
  const [retrievalResults, setRetrievalResults] = useState<KnowledgeBaseQueryResult[]>([]);
  const [retrievalResultCount, setRetrievalResultCount] = useState<number | null>(null);
  const [isResyncing, setIsResyncing] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (!token || !knowledgeBaseId) {
      return;
    }
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const [knowledgeBasePayload, documentsPayload] = await Promise.all([
          getKnowledgeBase(knowledgeBaseId, token),
          listKnowledgeBaseDocuments(knowledgeBaseId, token),
        ]);
        setKnowledgeBase(knowledgeBasePayload);
        setDocuments(documentsPayload);
        setForm({
          slug: knowledgeBasePayload.slug,
          displayName: knowledgeBasePayload.display_name,
          description: knowledgeBasePayload.description,
          lifecycleState: knowledgeBasePayload.lifecycle_state,
        });
      } catch (requestError) {
        showErrorFeedback(requestError, t("contextManagement.feedback.loadFailed"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [knowledgeBaseId, showErrorFeedback, t, token]);

  async function reload(): Promise<void> {
    if (!token || !knowledgeBaseId) {
      return;
    }
    const [knowledgeBasePayload, documentsPayload] = await Promise.all([
      getKnowledgeBase(knowledgeBaseId, token),
      listKnowledgeBaseDocuments(knowledgeBaseId, token),
    ]);
    setKnowledgeBase(knowledgeBasePayload);
    setDocuments(documentsPayload);
  }

  async function handleSaveKnowledgeBase(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      const updated = await updateKnowledgeBase(knowledgeBase.id, {
        slug: form.slug,
        display_name: form.displayName,
        description: form.description,
        lifecycle_state: form.lifecycleState,
      }, token);
      setKnowledgeBase(updated);
      showSuccessFeedback(t("contextManagement.feedback.updated", { name: updated.display_name }));
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.updateFailed"));
    }
  }

  async function handleSubmitDocument(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      if (documentForm.id) {
        await updateKnowledgeBaseDocument(knowledgeBase.id, documentForm.id, {
          title: documentForm.title,
          source_type: "manual",
          source_name: documentForm.sourceName || null,
          uri: documentForm.uri || null,
          text: documentForm.text,
        }, token);
        showSuccessFeedback(t("contextManagement.feedback.documentUpdated", { title: documentForm.title }));
      } else {
        await createKnowledgeBaseDocument(knowledgeBase.id, {
          title: documentForm.title,
          source_type: "manual",
          source_name: documentForm.sourceName || null,
          uri: documentForm.uri || null,
          text: documentForm.text,
        }, token);
        showSuccessFeedback(t("contextManagement.feedback.documentCreated", { title: documentForm.title }));
      }
      setDocumentForm(EMPTY_DOCUMENT_FORM);
      await reload();
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.documentSaveFailed"));
    }
  }

  async function handleDeleteDocument(documentId: string): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeBaseDocument(knowledgeBase.id, documentId, token);
      showSuccessFeedback(t("contextManagement.feedback.documentDeleted"));
      await reload();
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.documentDeleteFailed"));
    }
  }

  async function handleUpload(): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin || uploadFiles.length === 0) {
      return;
    }
    try {
      await uploadKnowledgeBaseDocuments(knowledgeBase.id, uploadFiles, token);
      setUploadFiles([]);
      showSuccessFeedback(t("contextManagement.feedback.uploaded", { count: uploadFiles.length }));
      await reload();
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.uploadFailed"));
    }
  }

  async function handleDeleteKnowledgeBase(): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeBase(knowledgeBase.id, token);
      navigate("/control/context", {
        state: withActionFeedbackState({
          kind: "success",
          message: t("contextManagement.feedback.deleted", { name: knowledgeBase.display_name }),
        }),
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.deleteFailed"));
    }
  }

  async function handleResyncKnowledgeBase(): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin || isResyncing) {
      return;
    }
    setIsResyncing(true);
    try {
      const refreshed = await resyncKnowledgeBase(knowledgeBase.id, token);
      setKnowledgeBase(refreshed);
      await reload();
      showSuccessFeedback(t("contextManagement.feedback.resynced", { name: refreshed.display_name }));
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.resyncFailed"));
    } finally {
      setIsResyncing(false);
    }
  }

  async function handleTestRetrieval(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !knowledgeBase || isQuerying) {
      return;
    }
    setIsQuerying(true);
    try {
      const response = await queryKnowledgeBase(
        knowledgeBase.id,
        {
          query_text: retrievalQuery,
          top_k: Number.parseInt(retrievalTopK, 10) || 5,
        },
        token,
      );
      setRetrievalResults(response.results);
      setRetrievalResultCount(response.retrieval.result_count);
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.queryFailed"));
    } finally {
      setIsQuerying(false);
    }
  }

  return (
    <section className="card-stack">
      <div className="platform-card-header panel">
        <div className="card-stack">
          <h2 className="section-title">{knowledgeBase?.display_name ?? t("contextManagement.detailTitle")}</h2>
          <p className="status-text">{knowledgeBase?.description || t("contextManagement.detailDescription")}</p>
        </div>
        <Link className="btn btn-secondary" to="/control/context">
          {t("contextManagement.actions.back")}
        </Link>
      </div>

      {loading ? <section className="panel"><p className="status-text">{t("contextManagement.states.loading")}</p></section> : null}

      {knowledgeBase ? (
        <>
          <section className="panel card-stack">
            <div className="status-row">
              <span className="platform-badge" data-tone={knowledgeBase.sync_status === "ready" ? "enabled" : "disabled"}>
                {`${knowledgeBase.lifecycle_state} / ${knowledgeBase.sync_status}`}
              </span>
              <span className="status-text">{knowledgeBase.index_name}</span>
            </div>
            <div className="card-stack">
              <p className="status-text">
                {knowledgeBase.eligible_for_binding
                  ? t("contextManagement.states.eligible")
                  : t("contextManagement.states.ineligible")}
              </p>
              {knowledgeBase.last_sync_summary ? <p className="status-text">{knowledgeBase.last_sync_summary}</p> : null}
              {knowledgeBase.last_sync_at ? (
                <p className="status-text">
                  {t("contextManagement.fields.lastSyncAt")}: {knowledgeBase.last_sync_at}
                </p>
              ) : null}
              {knowledgeBase.last_sync_error ? (
                <p className="status-text error-text">
                  {t("contextManagement.fields.lastSyncError")}: {knowledgeBase.last_sync_error}
                </p>
              ) : null}
            </div>
            {isSuperadmin ? (
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={isResyncing}
                  onClick={() => void handleResyncKnowledgeBase()}
                >
                  {isResyncing ? t("contextManagement.actions.resyncing") : t("contextManagement.actions.resync")}
                </button>
              </div>
            ) : null}
            <form className="card-stack" onSubmit={(event) => void handleSaveKnowledgeBase(event)}>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
                <input className="field-input" value={form.slug} disabled={!isSuperadmin} onChange={(event) => setForm((current) => ({ ...current, slug: event.currentTarget.value }))} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
                <input className="field-input" value={form.displayName} disabled={!isSuperadmin} onChange={(event) => setForm((current) => ({ ...current, displayName: event.currentTarget.value }))} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
                <textarea className="field-input quote-admin-textarea" value={form.description} disabled={!isSuperadmin} onChange={(event) => setForm((current) => ({ ...current, description: event.currentTarget.value }))} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.fields.lifecycleState")}</span>
                <select className="field-input" value={form.lifecycleState} disabled={!isSuperadmin} onChange={(event) => setForm((current) => ({ ...current, lifecycleState: event.currentTarget.value }))}>
                  <option value="active">active</option>
                  <option value="archived">archived</option>
                </select>
              </label>
              {isSuperadmin ? (
                <div className="form-actions">
                  <button type="submit" className="btn btn-primary">{t("contextManagement.actions.save")}</button>
                  <button type="button" className="btn btn-danger" onClick={() => void handleDeleteKnowledgeBase()}>
                    {t("contextManagement.actions.delete")}
                  </button>
                </div>
              ) : null}
            </form>
          </section>

          <section className="panel card-stack">
            <div className="platform-card-header">
              <div className="card-stack">
                <h3 className="section-title">{t("contextManagement.queryTitle")}</h3>
                <p className="status-text">{t("contextManagement.queryDescription")}</p>
              </div>
            </div>
            <form className="card-stack" onSubmit={(event) => void handleTestRetrieval(event)}>
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.fields.queryText")}</span>
                <textarea
                  className="field-input quote-admin-textarea"
                  value={retrievalQuery}
                  onChange={(event) => setRetrievalQuery(event.currentTarget.value)}
                />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.fields.topK")}</span>
                <input
                  className="field-input"
                  type="number"
                  min={1}
                  step={1}
                  value={retrievalTopK}
                  onChange={(event) => setRetrievalTopK(event.currentTarget.value)}
                />
              </label>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={isQuerying || !retrievalQuery.trim()}>
                  {isQuerying ? t("contextManagement.actions.querying") : t("contextManagement.actions.testRetrieval")}
                </button>
              </div>
            </form>
            {retrievalResultCount !== null ? (
              <p className="status-text">
                {t("contextManagement.states.queryResultCount", { count: retrievalResultCount })}
              </p>
            ) : null}
            {retrievalResults.length === 0 && retrievalResultCount !== null ? (
              <p className="status-text">{t("contextManagement.states.noQueryResults")}</p>
            ) : null}
            {retrievalResults.map((result) => (
              <article key={result.id} className="panel card-stack">
                <div className="platform-card-header">
                  <div className="card-stack">
                    <h4 className="section-title">{result.title || result.id}</h4>
                    <p className="status-text">
                      {result.score != null && result.score_kind
                        ? `${result.score_kind}: ${result.score}`
                        : result.source_type ?? ""}
                    </p>
                  </div>
                </div>
                {result.uri ? <p className="status-text">{result.uri}</p> : null}
                <p className="status-text">{result.snippet}</p>
              </article>
            ))}
          </section>

          <section className="panel card-stack">
            <h3 className="section-title">{t("contextManagement.documentsTitle")}</h3>
            {knowledgeBase.deployment_usage?.length ? (
              <div className="card-stack">
                <p className="status-text">{t("contextManagement.usageTitle")}</p>
                {knowledgeBase.deployment_usage.map((usage) => (
                  <p key={`${usage.deployment_profile.id}-${usage.capability}`} className="status-text">
                    <strong>{usage.deployment_profile.display_name}</strong> ({usage.deployment_profile.slug}) - {usage.capability}
                  </p>
                ))}
              </div>
            ) : null}

            {isSuperadmin ? (
              <>
                <form className="card-stack" onSubmit={(event) => void handleSubmitDocument(event)}>
                  <label className="card-stack">
                    <span className="field-label">{t("contextManagement.fields.documentTitle")}</span>
                    <input className="field-input" value={documentForm.title} onChange={(event) => setDocumentForm((current) => ({ ...current, title: event.currentTarget.value }))} />
                  </label>
                  <label className="card-stack">
                    <span className="field-label">{t("contextManagement.fields.sourceName")}</span>
                    <input className="field-input" value={documentForm.sourceName} onChange={(event) => setDocumentForm((current) => ({ ...current, sourceName: event.currentTarget.value }))} />
                  </label>
                  <label className="card-stack">
                    <span className="field-label">{t("contextManagement.fields.uri")}</span>
                    <input className="field-input" value={documentForm.uri} onChange={(event) => setDocumentForm((current) => ({ ...current, uri: event.currentTarget.value }))} />
                  </label>
                  <label className="card-stack">
                    <span className="field-label">{t("contextManagement.fields.documentText")}</span>
                    <textarea className="field-input quote-admin-textarea" value={documentForm.text} onChange={(event) => setDocumentForm((current) => ({ ...current, text: event.currentTarget.value }))} />
                  </label>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary">
                      {documentForm.id ? t("contextManagement.actions.updateDocument") : t("contextManagement.actions.addDocument")}
                    </button>
                    {documentForm.id ? (
                      <button type="button" className="btn btn-secondary" onClick={() => setDocumentForm(EMPTY_DOCUMENT_FORM)}>
                        {t("platformControl.actions.cancel")}
                      </button>
                    ) : null}
                  </div>
                </form>

                <div className="card-stack">
                  <label className="card-stack">
                    <span className="field-label">{t("contextManagement.fields.uploadFiles")}</span>
                    <input
                      className="field-input"
                      type="file"
                      multiple
                      onChange={(event) => setUploadFiles(Array.from(event.currentTarget.files ?? []))}
                    />
                  </label>
                  <div className="form-actions">
                    <button type="button" className="btn btn-secondary" disabled={uploadFiles.length === 0} onClick={() => void handleUpload()}>
                      {t("contextManagement.actions.upload")}
                    </button>
                  </div>
                </div>
              </>
            ) : null}

            {documents.length === 0 ? <p className="status-text">{t("contextManagement.states.noDocuments")}</p> : null}
            {documents.map((document) => (
              <article key={document.id} className="panel card-stack">
                <div className="platform-card-header">
                  <div className="card-stack">
                    <h4 className="section-title">{document.title}</h4>
                    <p className="status-text">{document.source_name || document.source_type}</p>
                  </div>
                  {isSuperadmin ? (
                    <div className="form-actions">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setDocumentForm({
                          id: document.id,
                          title: document.title,
                          sourceName: document.source_name ?? "",
                          uri: document.uri ?? "",
                          text: document.text,
                        })}
                      >
                        {t("contextManagement.actions.edit")}
                      </button>
                      <button type="button" className="btn btn-danger" onClick={() => void handleDeleteDocument(document.id)}>
                        {t("contextManagement.actions.deleteDocument")}
                      </button>
                    </div>
                  ) : null}
                </div>
                <p className="status-text">{document.uri}</p>
                <pre className="status-text" style={{ whiteSpace: "pre-wrap" }}>{document.text}</pre>
              </article>
            ))}
          </section>
        </>
      ) : null}
    </section>
  );
}
