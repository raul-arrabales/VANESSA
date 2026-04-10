import { useTranslation } from "react-i18next";
import type { KnowledgeBaseSchemaProperty } from "../../../api/context";
import type {
  KnowledgeBaseRetrievalActions,
  KnowledgeBaseRetrievalFormState,
  KnowledgeBaseRetrievalRunState,
} from "../hooks/useContextKnowledgeBaseRetrieval";
import { KnowledgeBaseRetrievalResults } from "./KnowledgeBaseRetrievalResults";
import { KnowledgeBaseRetrievalSettingsForm } from "./KnowledgeBaseRetrievalSettingsForm";

type Props = {
  schemaProperties: KnowledgeBaseSchemaProperty[];
  retrievalForm: KnowledgeBaseRetrievalFormState;
  retrievalRun: KnowledgeBaseRetrievalRunState | null;
  retrievalActions: KnowledgeBaseRetrievalActions;
  isQuerying: boolean;
};

export function KnowledgeBaseRetrievalSection({
  schemaProperties,
  retrievalForm,
  retrievalRun,
  retrievalActions,
  isQuerying,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">{t("contextManagement.queryTitle")}</h3>
          <p className="status-text">{t("contextManagement.queryDescription")}</p>
        </div>
      </div>
      <KnowledgeBaseRetrievalSettingsForm
        schemaProperties={schemaProperties}
        retrievalQuery={retrievalForm.query}
        retrievalTopK={retrievalForm.topK}
        retrievalSearchMethod={retrievalForm.searchMethod}
        retrievalHybridAlpha={retrievalForm.hybridAlpha}
        retrievalQueryPreprocessing={retrievalForm.queryPreprocessing}
        retrievalFilters={retrievalForm.filters}
        isQuerying={isQuerying}
        onQueryChange={retrievalActions.setQuery}
        onTopKChange={retrievalActions.setTopK}
        onSearchMethodChange={retrievalActions.setSearchMethod}
        onHybridAlphaChange={retrievalActions.setHybridAlpha}
        onQueryPreprocessingChange={retrievalActions.setQueryPreprocessing}
        onFiltersChange={retrievalActions.setFilters}
        onSubmit={retrievalActions.submit}
      />
      <KnowledgeBaseRetrievalResults retrievalRun={retrievalRun} />
    </section>
  );
}
