import { type Dispatch, type FormEvent, type SetStateAction, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createKnowledgeBaseDocument,
  deleteKnowledgeBaseDocument,
  updateKnowledgeBaseDocument,
  uploadKnowledgeBaseDocuments,
} from "../../../api/context";
import { EMPTY_DOCUMENT_FORM, type DocumentFormState } from "../types";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export type ContextKnowledgeBaseUploadResult = ReturnType<typeof useContextKnowledgeBaseLoader> & {
  documentForm: DocumentFormState;
  uploadFiles: File[];
  setDocumentForm: Dispatch<SetStateAction<DocumentFormState>>;
  setUploadFiles: Dispatch<SetStateAction<File[]>>;
  handleSubmitDocument: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleDeleteDocument: (documentId: string) => Promise<void>;
  handleUpload: () => Promise<void>;
};

export function useContextKnowledgeBaseUpload(): ContextKnowledgeBaseUploadResult {
  const { t } = useTranslation("common");
  const workspace = useContextKnowledgeBaseLoader({ loadDocuments: true });
  const [documentForm, setDocumentForm] = useState<DocumentFormState>(EMPTY_DOCUMENT_FORM);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);

  async function handleSubmitDocument(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    try {
      if (documentForm.id) {
        await updateKnowledgeBaseDocument(
          workspace.knowledgeBase.id,
          documentForm.id,
          {
            title: documentForm.title,
            source_type: "manual",
            source_name: documentForm.sourceName || null,
            uri: documentForm.uri || null,
            text: documentForm.text,
          },
          workspace.token,
        );
        workspace.showSuccessFeedback(t("contextManagement.feedback.documentUpdated", { title: documentForm.title }));
      } else {
        await createKnowledgeBaseDocument(
          workspace.knowledgeBase.id,
          {
            title: documentForm.title,
            source_type: "manual",
            source_name: documentForm.sourceName || null,
            uri: documentForm.uri || null,
            text: documentForm.text,
          },
          workspace.token,
        );
        workspace.showSuccessFeedback(t("contextManagement.feedback.documentCreated", { title: documentForm.title }));
      }
      setDocumentForm(EMPTY_DOCUMENT_FORM);
      await workspace.reload();
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.documentSaveFailed"));
    }
  }

  async function handleDeleteDocument(documentId: string): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin) {
      return;
    }
    try {
      await deleteKnowledgeBaseDocument(workspace.knowledgeBase.id, documentId, workspace.token);
      workspace.showSuccessFeedback(t("contextManagement.feedback.documentDeleted"));
      if (documentForm.id === documentId) {
        setDocumentForm(EMPTY_DOCUMENT_FORM);
      }
      await workspace.reload();
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.documentDeleteFailed"));
    }
  }

  async function handleUpload(): Promise<void> {
    if (!workspace.token || !workspace.knowledgeBase || !workspace.isSuperadmin || uploadFiles.length === 0) {
      return;
    }
    try {
      await uploadKnowledgeBaseDocuments(workspace.knowledgeBase.id, uploadFiles, workspace.token);
      setUploadFiles([]);
      workspace.showSuccessFeedback(t("contextManagement.feedback.uploaded", { count: uploadFiles.length }));
      await workspace.reload();
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.uploadFailed"));
    }
  }

  return {
    ...workspace,
    documentForm,
    uploadFiles,
    setDocumentForm,
    setUploadFiles,
    handleSubmitDocument,
    handleDeleteDocument,
    handleUpload,
  };
}
