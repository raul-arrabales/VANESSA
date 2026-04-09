import { useTranslation } from "react-i18next";
import type {
  KnowledgeBaseRetrievalActions,
  KnowledgeBaseRetrievalFormState,
  KnowledgeBaseRetrievalRunState,
} from "../hooks/useContextKnowledgeBaseRetrieval";
import { KnowledgeBaseRetrievalResults } from "./KnowledgeBaseRetrievalResults";
import { KnowledgeBaseRetrievalSettingsForm } from "./KnowledgeBaseRetrievalSettingsForm";

type Props = {
  retrievalForm: KnowledgeBaseRetrievalFormState;
  retrievalRun: KnowledgeBaseRetrievalRunState | null;
  retrievalActions: KnowledgeBaseRetrievalActions;
  isQuerying: boolean;
};

export function KnowledgeBaseRetrievalSection({
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
        retrievalQuery={retrievalForm.query}
        retrievalTopK={retrievalForm.topK}
        retrievalSearchMethod={retrievalForm.searchMethod}
        retrievalHybridAlpha={retrievalForm.hybridAlpha}
        retrievalQueryPreprocessing={retrievalForm.queryPreprocessing}
        isQuerying={isQuerying}
        onQueryChange={retrievalActions.setQuery}
        onTopKChange={retrievalActions.setTopK}
        onSearchMethodChange={retrievalActions.setSearchMethod}
        onHybridAlphaChange={retrievalActions.setHybridAlpha}
        onQueryPreprocessingChange={retrievalActions.setQueryPreprocessing}
        onSubmit={retrievalActions.submit}
      />
      <KnowledgeBaseRetrievalResults retrievalRun={retrievalRun} />
    </section>
  );
}
