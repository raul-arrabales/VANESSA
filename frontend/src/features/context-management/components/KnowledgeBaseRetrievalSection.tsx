import { type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type {
  KnowledgeBaseQueryPreprocessing,
  KnowledgeBaseQueryResult,
  KnowledgeBaseSearchMethod,
} from "../../../api/context";
import { KnowledgeBaseRetrievalResults } from "./KnowledgeBaseRetrievalResults";
import { KnowledgeBaseRetrievalSettingsForm } from "./KnowledgeBaseRetrievalSettingsForm";

type Props = {
  retrievalQuery: string;
  retrievalTopK: string;
  retrievalSearchMethod: KnowledgeBaseSearchMethod;
  retrievalHybridAlpha: string;
  retrievalQueryPreprocessing: KnowledgeBaseQueryPreprocessing;
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
  retrievalDurationMs: number | null;
  completedQueryId: number;
  isQuerying: boolean;
  onQueryChange: Dispatch<SetStateAction<string>>;
  onTopKChange: Dispatch<SetStateAction<string>>;
  onSearchMethodChange: Dispatch<SetStateAction<KnowledgeBaseSearchMethod>>;
  onHybridAlphaChange: Dispatch<SetStateAction<string>>;
  onQueryPreprocessingChange: Dispatch<SetStateAction<KnowledgeBaseQueryPreprocessing>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function KnowledgeBaseRetrievalSection({
  retrievalQuery,
  retrievalTopK,
  retrievalSearchMethod,
  retrievalHybridAlpha,
  retrievalQueryPreprocessing,
  retrievalResults,
  retrievalResultCount,
  retrievalDurationMs,
  completedQueryId,
  isQuerying,
  onQueryChange,
  onTopKChange,
  onSearchMethodChange,
  onHybridAlphaChange,
  onQueryPreprocessingChange,
  onSubmit,
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
        retrievalQuery={retrievalQuery}
        retrievalTopK={retrievalTopK}
        retrievalSearchMethod={retrievalSearchMethod}
        retrievalHybridAlpha={retrievalHybridAlpha}
        retrievalQueryPreprocessing={retrievalQueryPreprocessing}
        isQuerying={isQuerying}
        onQueryChange={onQueryChange}
        onTopKChange={onTopKChange}
        onSearchMethodChange={onSearchMethodChange}
        onHybridAlphaChange={onHybridAlphaChange}
        onQueryPreprocessingChange={onQueryPreprocessingChange}
        onSubmit={onSubmit}
      />
      <KnowledgeBaseRetrievalResults
        retrievalResults={retrievalResults}
        retrievalResultCount={retrievalResultCount}
        retrievalDurationMs={retrievalDurationMs}
        completedQueryId={completedQueryId}
      />
    </section>
  );
}
