import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  createKnowledgeBaseDocument,
  createKnowledgeSource,
  deleteKnowledgeBase,
  deleteKnowledgeBaseDocument,
  deleteKnowledgeSource,
  getKnowledgeSourceDirectories,
  getKnowledgeBase,
  listKnowledgeBaseDocuments,
  listKnowledgeSources,
  listKnowledgeSyncRuns,
  queryKnowledgeBase,
  resyncKnowledgeBase,
  syncKnowledgeSource,
  updateKnowledgeBase,
  updateKnowledgeBaseDocument,
  updateKnowledgeSource,
  uploadKnowledgeBaseDocuments,
} from "../../../api/context";
import type { KnowledgeSourceDirectoriesResponse } from "../../../api/context";
import { useAuth } from "../../../auth/AuthProvider";
import {
  useActionFeedback,
  useRouteActionFeedback,
  withActionFeedbackState,
} from "../../../feedback/ActionFeedbackProvider";
import {
  EMPTY_DOCUMENT_FORM,
  createEmptySourceForm,
  parseGlobText,
  type ContextKnowledgeBaseDetailState,
  type DocumentFormState,
  type SourceFormState,
} from "../types";

type UseContextKnowledgeBaseDetailResult = ContextKnowledgeBaseDetailState & {
  reload: () => Promise<void>;
  setForm: Dispatch<
    SetStateAction<{
      slug: string;
      displayName: string;
      description: string;
      lifecycleState: string;
    }>
  >;
  setDocumentForm: Dispatch<SetStateAction<DocumentFormState>>;
  setSourceForm: Dispatch<SetStateAction<SourceFormState>>;
  setUploadFiles: Dispatch<SetStateAction<File[]>>;
  setRetrievalQuery: Dispatch<SetStateAction<string>>;
  setRetrievalTopK: Dispatch<SetStateAction<string>>;
  handleSaveKnowledgeBase: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleSubmitDocument: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleDeleteDocument: (documentId: string) => Promise<void>;
  handleUpload: () => Promise<void>;
  handleDeleteKnowledgeBase: () => Promise<void>;
  handleResyncKnowledgeBase: () => Promise<void>;
  handleSubmitSource: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleDeleteSource: (sourceId: string) => Promise<void>;
  handleSyncSource: (sourceId: string) => Promise<void>;
  sourceDirectoryBrowser: {
    open: boolean;
    loading: boolean;
    payload: KnowledgeSourceDirectoriesResponse | null;
  };
  handleOpenSourceDirectoryBrowser: () => Promise<void>;
  handleCloseSourceDirectoryBrowser: () => void;
  handleBrowseSourceDirectories: (rootId: string | null, relativePath: string | null) => Promise<void>;
  handleUseCurrentSourceDirectory: () => void;
  handleTestRetrieval: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function useContextKnowledgeBaseDetail(): UseContextKnowledgeBaseDetailResult {
  const { t } = useTranslation("common");
  const { knowledgeBaseId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, user } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const isSuperadmin = user?.role === "superadmin";
  const [knowledgeBase, setKnowledgeBase] = useState<UseContextKnowledgeBaseDetailResult["knowledgeBase"]>(null);
  const [documents, setDocuments] = useState<UseContextKnowledgeBaseDetailResult["documents"]>([]);
  const [sources, setSources] = useState<UseContextKnowledgeBaseDetailResult["sources"]>([]);
  const [syncRuns, setSyncRuns] = useState<UseContextKnowledgeBaseDetailResult["syncRuns"]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    slug: "",
    displayName: "",
    description: "",
    lifecycleState: "active",
  });
  const [documentForm, setDocumentForm] = useState<DocumentFormState>(EMPTY_DOCUMENT_FORM);
  const [sourceForm, setSourceForm] = useState<SourceFormState>(createEmptySourceForm);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalTopK, setRetrievalTopK] = useState("5");
  const [retrievalResults, setRetrievalResults] = useState<UseContextKnowledgeBaseDetailResult["retrievalResults"]>([]);
  const [retrievalResultCount, setRetrievalResultCount] = useState<number | null>(null);
  const [isResyncing, setIsResyncing] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);
  const [sourceDirectoryBrowserOpen, setSourceDirectoryBrowserOpen] = useState(false);
  const [sourceDirectoryBrowserLoading, setSourceDirectoryBrowserLoading] = useState(false);
  const [sourceDirectoryBrowserPayload, setSourceDirectoryBrowserPayload] = useState<KnowledgeSourceDirectoriesResponse | null>(null);

  useRouteActionFeedback(location.state);

  const reload = async (): Promise<void> => {
    if (!token || !knowledgeBaseId) {
      return;
    }
    const [knowledgeBasePayload, documentsPayload, sourcesPayload, syncRunsPayload] = await Promise.all([
      getKnowledgeBase(knowledgeBaseId, token),
      listKnowledgeBaseDocuments(knowledgeBaseId, token),
      listKnowledgeSources(knowledgeBaseId, token),
      listKnowledgeSyncRuns(knowledgeBaseId, token),
    ]);
    setKnowledgeBase(knowledgeBasePayload);
    setDocuments(documentsPayload);
    setSources(sourcesPayload);
    setSyncRuns(syncRunsPayload);
  };

  useEffect(() => {
    if (!token || !knowledgeBaseId) {
      return;
    }
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const [knowledgeBasePayload, documentsPayload, sourcesPayload, syncRunsPayload] = await Promise.all([
          getKnowledgeBase(knowledgeBaseId, token),
          listKnowledgeBaseDocuments(knowledgeBaseId, token),
          listKnowledgeSources(knowledgeBaseId, token),
          listKnowledgeSyncRuns(knowledgeBaseId, token),
        ]);
        setKnowledgeBase(knowledgeBasePayload);
        setDocuments(documentsPayload);
        setSources(sourcesPayload);
        setSyncRuns(syncRunsPayload);
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

  async function handleSaveKnowledgeBase(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      const updated = await updateKnowledgeBase(
        knowledgeBase.id,
        {
          slug: form.slug,
          display_name: form.displayName,
          description: form.description,
          lifecycle_state: form.lifecycleState,
        },
        token,
      );
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
        await updateKnowledgeBaseDocument(
          knowledgeBase.id,
          documentForm.id,
          {
            title: documentForm.title,
            source_type: "manual",
            source_name: documentForm.sourceName || null,
            uri: documentForm.uri || null,
            text: documentForm.text,
          },
          token,
        );
        showSuccessFeedback(t("contextManagement.feedback.documentUpdated", { title: documentForm.title }));
      } else {
        await createKnowledgeBaseDocument(
          knowledgeBase.id,
          {
            title: documentForm.title,
            source_type: "manual",
            source_name: documentForm.sourceName || null,
            uri: documentForm.uri || null,
            text: documentForm.text,
          },
          token,
        );
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

  async function handleSubmitSource(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    const payload = {
      display_name: sourceForm.displayName,
      relative_path: sourceForm.relativePath,
      include_globs: parseGlobText(sourceForm.includeGlobs),
      exclude_globs: parseGlobText(sourceForm.excludeGlobs),
      lifecycle_state: sourceForm.lifecycleState,
      source_type: "local_directory",
    };
    try {
      if (sourceForm.id) {
        await updateKnowledgeSource(knowledgeBase.id, sourceForm.id, payload, token);
        showSuccessFeedback(t("contextManagement.feedback.sourceUpdated", { name: sourceForm.displayName }));
      } else {
        await createKnowledgeSource(knowledgeBase.id, payload, token);
        showSuccessFeedback(t("contextManagement.feedback.sourceCreated", { name: sourceForm.displayName }));
      }
      setSourceForm(createEmptySourceForm());
      setSourceDirectoryBrowserOpen(false);
      setSourceDirectoryBrowserPayload(null);
      await reload();
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.sourceSaveFailed"));
    }
  }

  async function handleDeleteSource(sourceId: string): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeSource(knowledgeBase.id, sourceId, token);
      if (sourceForm.id === sourceId) {
        setSourceForm(createEmptySourceForm());
        setSourceDirectoryBrowserOpen(false);
        setSourceDirectoryBrowserPayload(null);
      }
      showSuccessFeedback(t("contextManagement.feedback.sourceDeleted"));
      await reload();
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.sourceDeleteFailed"));
    }
  }

  async function handleBrowseSourceDirectories(rootId: string | null, relativePath: string | null): Promise<void> {
    if (!token) {
      return;
    }
    setSourceDirectoryBrowserLoading(true);
    try {
      const payload = await getKnowledgeSourceDirectories(token, { rootId, relativePath });
      setSourceDirectoryBrowserPayload(payload);
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.sourceDirectoriesLoadFailed"));
    } finally {
      setSourceDirectoryBrowserLoading(false);
    }
  }

  async function handleOpenSourceDirectoryBrowser(): Promise<void> {
    setSourceDirectoryBrowserOpen(true);
    await handleBrowseSourceDirectories(sourceDirectoryBrowserPayload?.selected_root_id ?? null, sourceForm.relativePath || null);
  }

  function handleCloseSourceDirectoryBrowser(): void {
    setSourceDirectoryBrowserOpen(false);
  }

  function handleUseCurrentSourceDirectory(): void {
    const currentRelativePath = sourceDirectoryBrowserPayload?.current_relative_path ?? "";
    if (!currentRelativePath) {
      return;
    }
    setSourceForm((current) => ({ ...current, relativePath: currentRelativePath }));
    setSourceDirectoryBrowserOpen(false);
  }

  async function handleSyncSource(sourceId: string): Promise<void> {
    if (!token || !knowledgeBase || !isSuperadmin || syncingSourceId) {
      return;
    }
    setSyncingSourceId(sourceId);
    try {
      const response = await syncKnowledgeSource(knowledgeBase.id, sourceId, token);
      setKnowledgeBase(response.knowledge_base);
      await reload();
      showSuccessFeedback(t("contextManagement.feedback.sourceSynced", { name: response.source.display_name }));
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.sourceSyncFailed"));
    } finally {
      setSyncingSourceId(null);
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

  return {
    knowledgeBase,
    documents,
    sources,
    syncRuns,
    loading,
    isSuperadmin,
    form,
    documentForm,
    sourceForm,
    sourceDirectoryBrowser: {
      open: sourceDirectoryBrowserOpen,
      loading: sourceDirectoryBrowserLoading,
      payload: sourceDirectoryBrowserPayload,
    },
    uploadFiles,
    retrievalQuery,
    retrievalTopK,
    retrievalResults,
    retrievalResultCount,
    isResyncing,
    isQuerying,
    syncingSourceId,
    reload,
    setForm,
    setDocumentForm,
    setSourceForm,
    setUploadFiles,
    setRetrievalQuery,
    setRetrievalTopK,
    handleSaveKnowledgeBase,
    handleSubmitDocument,
    handleDeleteDocument,
    handleUpload,
    handleDeleteKnowledgeBase,
    handleResyncKnowledgeBase,
    handleSubmitSource,
    handleDeleteSource,
    handleSyncSource,
    handleOpenSourceDirectoryBrowser,
    handleCloseSourceDirectoryBrowser,
    handleBrowseSourceDirectories,
    handleUseCurrentSourceDirectory,
    handleTestRetrieval,
  };
}
