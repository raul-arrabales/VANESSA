import { type Dispatch, type FormEvent, type SetStateAction, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createKnowledgeSource,
  deleteKnowledgeSource,
  getKnowledgeSourceDirectories,
  syncKnowledgeSource,
  updateKnowledgeSource,
} from "../../../api/context";
import type { KnowledgeSourceDirectoriesResponse } from "../../../api/context";
import { createEmptySourceForm, parseGlobText, type SourceFormState } from "../types";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

function normalizeRelativePath(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .replace(/^\/+|\/+$/g, "");
}

export type ContextKnowledgeBaseSourcesResult = ReturnType<typeof useContextKnowledgeBaseLoader> & {
  sourceForm: SourceFormState;
  sourceDirectoryBrowser: {
    open: boolean;
    loading: boolean;
    payload: KnowledgeSourceDirectoriesResponse | null;
    usedPaths: Set<string>;
    currentPathUsed: boolean;
  };
  syncingSourceId: string | null;
  setSourceForm: Dispatch<SetStateAction<SourceFormState>>;
  handleSubmitSource: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleDeleteSource: (sourceId: string) => Promise<void>;
  handleSyncSource: (sourceId: string) => Promise<void>;
  handleOpenSourceDirectoryBrowser: () => Promise<void>;
  handleCloseSourceDirectoryBrowser: () => void;
  handleBrowseSourceDirectories: (rootId: string | null, relativePath: string | null) => Promise<void>;
  handleSelectAndBrowseSourceDirectory: (rootId: string | null, relativePath: string) => Promise<void>;
  handleUseCurrentSourceDirectory: () => void;
};

export function useContextKnowledgeBaseSources(): ContextKnowledgeBaseSourcesResult {
  const { t } = useTranslation("common");
  const workspace = useContextKnowledgeBaseLoader({ loadSources: true, loadSyncRuns: true });
  const [sourceForm, setSourceForm] = useState<SourceFormState>(createEmptySourceForm);
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);
  const [sourceDirectoryBrowserOpen, setSourceDirectoryBrowserOpen] = useState(false);
  const [sourceDirectoryBrowserLoading, setSourceDirectoryBrowserLoading] = useState(false);
  const [sourceDirectoryBrowserPayload, setSourceDirectoryBrowserPayload] = useState<KnowledgeSourceDirectoriesResponse | null>(null);
  const currentSourceId = sourceForm.id;
  const usedPaths = useMemo(() => {
    const next = new Set<string>();
    workspace.sources.forEach((source) => {
      if (currentSourceId && source.id === currentSourceId) {
        return;
      }
      const normalizedPath = normalizeRelativePath(source.relative_path);
      if (normalizedPath) {
        next.add(normalizedPath);
      }
    });
    return next;
  }, [currentSourceId, workspace.sources]);
  const currentBrowserPath = normalizeRelativePath(sourceDirectoryBrowserPayload?.current_relative_path);
  const currentPathUsed = currentBrowserPath ? usedPaths.has(currentBrowserPath) : false;

  async function handleSubmitSource(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    const normalizedRelativePath = normalizeRelativePath(sourceForm.relativePath);
    if (normalizedRelativePath && usedPaths.has(normalizedRelativePath)) {
      workspace.showErrorFeedback(
        t("contextManagement.feedback.sourcePathUsed"),
        t("contextManagement.feedback.sourceSaveFailed"),
      );
      return;
    }
    const payload = {
      display_name: sourceForm.displayName,
      relative_path: normalizedRelativePath,
      include_globs: parseGlobText(sourceForm.includeGlobs),
      exclude_globs: parseGlobText(sourceForm.excludeGlobs),
      lifecycle_state: sourceForm.lifecycleState,
      source_type: "local_directory",
    };
    try {
      if (sourceForm.id) {
        await updateKnowledgeSource(workspace.knowledgeBase.id, sourceForm.id, payload, workspace.token);
        workspace.showSuccessFeedback(t("contextManagement.feedback.sourceUpdated", { name: sourceForm.displayName }));
      } else {
        await createKnowledgeSource(workspace.knowledgeBase.id, payload, workspace.token);
        workspace.showSuccessFeedback(t("contextManagement.feedback.sourceCreated", { name: sourceForm.displayName }));
      }
      setSourceForm(createEmptySourceForm());
      setSourceDirectoryBrowserOpen(false);
      setSourceDirectoryBrowserPayload(null);
      await workspace.reload();
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.sourceSaveFailed"));
    }
  }

  async function handleDeleteSource(sourceId: string): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeSource(workspace.knowledgeBase.id, sourceId, workspace.token);
      if (sourceForm.id === sourceId) {
        setSourceForm(createEmptySourceForm());
        setSourceDirectoryBrowserOpen(false);
        setSourceDirectoryBrowserPayload(null);
      }
      workspace.showSuccessFeedback(t("contextManagement.feedback.sourceDeleted"));
      await workspace.reload();
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.sourceDeleteFailed"));
    }
  }

  async function handleBrowseSourceDirectories(rootId: string | null, relativePath: string | null): Promise<void> {
    if (!workspace.token) {
      return;
    }
    setSourceDirectoryBrowserLoading(true);
    try {
      const payload = await getKnowledgeSourceDirectories(workspace.token, { rootId, relativePath });
      setSourceDirectoryBrowserPayload(payload);
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.sourceDirectoriesLoadFailed"));
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

  async function handleSelectAndBrowseSourceDirectory(rootId: string | null, relativePath: string): Promise<void> {
    const normalizedPath = normalizeRelativePath(relativePath);
    if (usedPaths.has(normalizedPath)) {
      return;
    }
    setSourceForm((current) => ({ ...current, relativePath: normalizedPath }));
    await handleBrowseSourceDirectories(rootId, relativePath);
  }

  function handleUseCurrentSourceDirectory(): void {
    const currentRelativePath = normalizeRelativePath(sourceDirectoryBrowserPayload?.current_relative_path);
    if (!currentRelativePath || usedPaths.has(currentRelativePath)) {
      return;
    }
    setSourceForm((current) => ({ ...current, relativePath: currentRelativePath }));
    setSourceDirectoryBrowserOpen(false);
  }

  async function handleSyncSource(sourceId: string): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin || syncingSourceId) {
      return;
    }
    setSyncingSourceId(sourceId);
    try {
      const response = await syncKnowledgeSource(workspace.knowledgeBase.id, sourceId, workspace.token);
      workspace.setKnowledgeBase(response.knowledge_base);
      await workspace.reload();
      workspace.showSuccessFeedback(t("contextManagement.feedback.sourceSynced", { name: response.source.display_name }));
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.sourceSyncFailed"));
    } finally {
      setSyncingSourceId(null);
    }
  }

  return {
    ...workspace,
    sourceForm,
    sourceDirectoryBrowser: {
      open: sourceDirectoryBrowserOpen,
      loading: sourceDirectoryBrowserLoading,
      payload: sourceDirectoryBrowserPayload,
      usedPaths,
      currentPathUsed,
    },
    syncingSourceId,
    setSourceForm,
    handleSubmitSource,
    handleDeleteSource,
    handleSyncSource,
    handleOpenSourceDirectoryBrowser,
    handleCloseSourceDirectoryBrowser,
    handleBrowseSourceDirectories,
    handleSelectAndBrowseSourceDirectory,
    handleUseCurrentSourceDirectory,
  };
}
