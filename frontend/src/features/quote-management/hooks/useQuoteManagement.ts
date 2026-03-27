import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../../auth/authApi";
import {
  createQuote,
  fetchQuoteById,
  fetchQuotes,
  fetchQuoteSummary,
  updateQuote,
  type QuoteAdminItem,
  type QuoteListFilters,
  type QuotePayload,
  type QuoteSummary,
} from "../../../api/quoteAdmin";

export type QuoteFormState = {
  language: string;
  text: string;
  author: string;
  source_universe: string;
  tone: string;
  tags: string;
  is_active: boolean;
  is_approved: boolean;
  origin: string;
  external_ref: string;
};

const PAGE_SIZE = 10;

export function blankQuoteForm(): QuoteFormState {
  return {
    language: "en",
    text: "",
    author: "",
    source_universe: "Original",
    tone: "reflective",
    tags: "",
    is_active: true,
    is_approved: true,
    origin: "local",
    external_ref: "",
  };
}

export function formFromQuote(quote: QuoteAdminItem): QuoteFormState {
  return {
    language: quote.language,
    text: quote.text,
    author: quote.author,
    source_universe: quote.source_universe,
    tone: quote.tone,
    tags: quote.tags.join(", "),
    is_active: quote.is_active,
    is_approved: quote.is_approved,
    origin: quote.origin,
    external_ref: quote.external_ref ?? "",
  };
}

export function formToPayload(form: QuoteFormState): QuotePayload {
  return {
    language: form.language,
    text: form.text,
    author: form.author,
    source_universe: form.source_universe,
    tone: form.tone,
    tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    is_active: form.is_active,
    is_approved: form.is_approved,
    origin: form.origin,
    external_ref: form.external_ref,
  };
}

type UseQuoteManagementResult = {
  summary: QuoteSummary | null;
  items: QuoteAdminItem[];
  selectedQuote: QuoteAdminItem | null;
  draft: QuoteFormState;
  filters: QuoteListFilters;
  filterDraft: QuoteListFilters;
  page: number;
  total: number;
  totalPages: number;
  isLoadingSummary: boolean;
  isLoadingList: boolean;
  isLoadingDetail: boolean;
  isSaving: boolean;
  isCreating: boolean;
  isEditorOpen: boolean;
  error: string;
  success: string;
  setDraft: Dispatch<SetStateAction<QuoteFormState>>;
  setFilterDraft: Dispatch<SetStateAction<QuoteListFilters>>;
  setPage: Dispatch<SetStateAction<number>>;
  submitSearch: () => void;
  beginCreate: () => void;
  closeEditor: () => void;
  selectQuote: (quoteId: number) => Promise<void>;
  saveQuote: () => Promise<void>;
};

export function useQuoteManagement(token: string): UseQuoteManagementResult {
  const { t } = useTranslation("common");
  const [summary, setSummary] = useState<QuoteSummary | null>(null);
  const [items, setItems] = useState<QuoteAdminItem[]>([]);
  const [selectedQuote, setSelectedQuote] = useState<QuoteAdminItem | null>(null);
  const [draft, setDraft] = useState<QuoteFormState>(blankQuoteForm);
  const [filters, setFilters] = useState<QuoteListFilters>({});
  const [filterDraft, setFilterDraft] = useState<QuoteListFilters>({});
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleError = useCallback((loadError: unknown): void => {
    if (loadError instanceof ApiError) {
      setError(loadError.message);
    } else {
      setError(t("auth.error.unknown"));
    }
  }, [t]);

  const loadSummary = useCallback(async (): Promise<void> => {
    setIsLoadingSummary(true);
    try {
      setSummary(await fetchQuoteSummary(token));
    } catch (loadError) {
      handleError(loadError);
    } finally {
      setIsLoadingSummary(false);
    }
  }, [handleError, token]);

  const loadQuotes = useCallback(async (nextPage: number, nextFilters: QuoteListFilters): Promise<void> => {
    setIsLoadingList(true);
    try {
      const result = await fetchQuotes(token, nextPage, PAGE_SIZE, nextFilters);
      setItems(result.items);
      setPage(result.page);
      setTotal(result.total);
    } catch (loadError) {
      handleError(loadError);
    } finally {
      setIsLoadingList(false);
    }
  }, [handleError, token]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    void loadQuotes(page, filters);
  }, [filters, loadQuotes, page]);

  const closeEditor = useCallback((): void => {
    setIsEditorOpen(false);
    setIsCreating(false);
    setSelectedQuote(null);
    setIsLoadingDetail(false);
    setDraft(blankQuoteForm());
  }, []);

  const selectQuote = useCallback(async (quoteId: number): Promise<void> => {
    setError("");
    setSuccess("");
    setIsCreating(false);
    setIsEditorOpen(true);
    setIsLoadingDetail(true);
    try {
      const quote = await fetchQuoteById(quoteId, token);
      setSelectedQuote(quote);
      setDraft(formFromQuote(quote));
    } catch (loadError) {
      handleError(loadError);
    } finally {
      setIsLoadingDetail(false);
    }
  }, [handleError, token]);

  const submitSearch = useCallback((): void => {
    setError("");
    setSuccess("");
    setPage(1);
    setFilters({ ...filterDraft });
  }, [filterDraft]);

  const beginCreate = useCallback((): void => {
    setIsCreating(true);
    setIsEditorOpen(true);
    setSelectedQuote(null);
    setDraft(blankQuoteForm());
    setError("");
    setSuccess("");
  }, []);

  const saveQuote = useCallback(async (): Promise<void> => {
    setError("");
    setSuccess("");
    setIsSaving(true);

    try {
      if (isCreating) {
        await createQuote(formToPayload(draft), token);
        setSuccess(t("quoteAdmin.feedback.created"));
        setIsCreating(false);
        await loadSummary();
        await loadQuotes(1, filters);
        setPage(1);
        closeEditor();
      } else if (selectedQuote) {
        await updateQuote(selectedQuote.id, formToPayload(draft), token);
        setSuccess(t("quoteAdmin.feedback.updated"));
        await loadSummary();
        await loadQuotes(page, filters);
        closeEditor();
      }
    } catch (submitError) {
      handleError(submitError);
    } finally {
      setIsSaving(false);
    }
  }, [closeEditor, draft, filters, handleError, isCreating, loadQuotes, loadSummary, page, selectedQuote, t, token]);

  return {
    summary,
    items,
    selectedQuote,
    draft,
    filters,
    filterDraft,
    page,
    total,
    totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
    isLoadingSummary,
    isLoadingList,
    isLoadingDetail,
    isSaving,
    isCreating,
    isEditorOpen,
    error,
    success,
    setDraft,
    setFilterDraft,
    setPage,
    submitSearch,
    beginCreate,
    closeEditor,
    selectQuote,
    saveQuote,
  };
}
