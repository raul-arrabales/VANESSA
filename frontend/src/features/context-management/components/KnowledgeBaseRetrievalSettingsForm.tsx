import { type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type {
  KnowledgeBaseQueryPreprocessing,
  KnowledgeBaseSchemaProperty,
  KnowledgeBaseSearchMethod,
} from "../../../api/context";
import { shouldShowHybridAlphaControl } from "../../ai-shared/retrieval";
import type { MetadataEntryFormState } from "../types";
import { KnowledgeBaseRetrievalFiltersEditor } from "./KnowledgeBaseRetrievalFiltersEditor";

type Props = {
  schemaProperties: KnowledgeBaseSchemaProperty[];
  retrievalQuery: string;
  retrievalTopK: string;
  retrievalSearchMethod: KnowledgeBaseSearchMethod;
  retrievalHybridAlpha: string;
  retrievalQueryPreprocessing: KnowledgeBaseQueryPreprocessing;
  retrievalFilters: MetadataEntryFormState[];
  isQuerying: boolean;
  onQueryChange: Dispatch<SetStateAction<string>>;
  onTopKChange: Dispatch<SetStateAction<string>>;
  onSearchMethodChange: Dispatch<SetStateAction<KnowledgeBaseSearchMethod>>;
  onHybridAlphaChange: Dispatch<SetStateAction<string>>;
  onQueryPreprocessingChange: Dispatch<SetStateAction<KnowledgeBaseQueryPreprocessing>>;
  onFiltersChange: Dispatch<SetStateAction<MetadataEntryFormState[]>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function KnowledgeBaseRetrievalSettingsForm({
  schemaProperties,
  retrievalQuery,
  retrievalTopK,
  retrievalSearchMethod,
  retrievalHybridAlpha,
  retrievalQueryPreprocessing,
  retrievalFilters,
  isQuerying,
  onQueryChange,
  onTopKChange,
  onSearchMethodChange,
  onHybridAlphaChange,
  onQueryPreprocessingChange,
  onFiltersChange,
  onSubmit,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <form className="card-stack" onSubmit={(event) => void onSubmit(event)}>
      <label className="card-stack">
        <span className="field-label">{t("contextManagement.fields.queryText")}</span>
        <textarea
          className="field-input form-textarea context-retrieval-query-textarea"
          rows={2}
          value={retrievalQuery}
          onChange={(event) => onQueryChange(event.currentTarget.value)}
        />
      </label>
      <section className="context-retrieval-settings card-stack" aria-labelledby="retrieval-settings-title">
        <div className="card-stack">
          <h4 id="retrieval-settings-title" className="field-label">
            {t("contextManagement.fields.retrievalSettings")}
          </h4>
        </div>
        <div className="context-retrieval-settings-row">
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.topK")}</span>
            <input
              className="field-input"
              type="number"
              min={1}
              step={1}
              value={retrievalTopK}
              onChange={(event) => onTopKChange(event.currentTarget.value)}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.searchMethod")}</span>
            <select
              className="field-input"
              value={retrievalSearchMethod}
              onChange={(event) => onSearchMethodChange(event.currentTarget.value as KnowledgeBaseSearchMethod)}
            >
              <option value="semantic">{t("contextManagement.searchMethods.semantic")}</option>
              <option value="keyword">{t("contextManagement.searchMethods.keyword")}</option>
              <option value="hybrid">{t("contextManagement.searchMethods.hybrid")}</option>
            </select>
          </label>
          {shouldShowHybridAlphaControl(retrievalSearchMethod) ? (
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.fields.hybridAlpha")}</span>
              <input
                className="field-input"
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={retrievalHybridAlpha}
                onChange={(event) => onHybridAlphaChange(event.currentTarget.value)}
              />
            </label>
          ) : null}
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.queryPreprocessing")}</span>
            <select
              className="field-input"
              value={retrievalQueryPreprocessing}
              onChange={(event) => onQueryPreprocessingChange(event.currentTarget.value as KnowledgeBaseQueryPreprocessing)}
            >
              <option value="none">{t("contextManagement.queryPreprocessing.none")}</option>
              <option value="normalize">{t("contextManagement.queryPreprocessing.normalize")}</option>
            </select>
          </label>
        </div>
        <KnowledgeBaseRetrievalFiltersEditor
          schemaProperties={schemaProperties}
          entries={retrievalFilters}
          onChange={onFiltersChange}
        />
      </section>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={isQuerying || !retrievalQuery.trim()}>
          {isQuerying ? t("contextManagement.actions.querying") : t("contextManagement.actions.testRetrieval")}
        </button>
      </div>
    </form>
  );
}
