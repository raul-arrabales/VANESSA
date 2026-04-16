import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import ModelSummaryCards from "../components/ModelSummaryCards";
import ModelOpsModelsSubmenu from "../components/ModelOpsModelsSubmenu";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import { useModelOpsSummary } from "../hooks/useModelOpsSummary";

export default function ModelOpsHomePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const role = user?.role;
  const { cards, error, isLoading } = useModelOpsSummary(token, role);

  return (
    <ModelOpsWorkspaceFrame secondaryNavigation={<ModelOpsModelsSubmenu activeView="summary" />}>
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.home.summaryTitle")}</h2>
        {isLoading ? <p className="status-text">{t("modelOps.states.loading")}</p> : <ModelSummaryCards items={cards} />}
        {error && <p className="error-text">{error}</p>}
      </article>
    </ModelOpsWorkspaceFrame>
  );
}
