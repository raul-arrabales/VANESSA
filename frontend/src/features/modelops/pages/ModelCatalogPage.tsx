import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ModelCatalogFilters from "../components/ModelCatalogFilters";
import ModelCatalogList from "../components/ModelCatalogList";
import ModelCatalogSubmenu from "../components/ModelCatalogSubmenu";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import { useModelCatalog } from "../hooks/useModelCatalog";
import { useAuth } from "../../../auth/AuthProvider";
import { canAccessModelTesting } from "../domain";

export default function ModelCatalogPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const { models, isLoading, error } = useModelCatalog(token);
  const [search, setSearch] = useState("");
  const [taskFilter, setTaskFilter] = useState("");
  const [hostingFilter, setHostingFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  const filteredModels = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return models.filter((model) => {
      const matchesSearch = !normalizedSearch
        || model.name.toLowerCase().includes(normalizedSearch)
        || model.id.toLowerCase().includes(normalizedSearch)
        || String(model.provider ?? "").toLowerCase().includes(normalizedSearch);
      const matchesTask = !taskFilter || model.task_key === taskFilter;
      const hosting = model.hosting ?? (model.backend === "local" ? "local" : "cloud");
      const matchesHosting = !hostingFilter || hosting === hostingFilter;
      const matchesState = !stateFilter || model.lifecycle_state === stateFilter;
      return matchesSearch && matchesTask && matchesHosting && matchesState;
    });
  }, [hostingFilter, models, search, stateFilter, taskFilter]);
  const canTest = canAccessModelTesting(user);

  return (
    <ModelOpsWorkspaceFrame secondaryNavigation={<ModelCatalogSubmenu activeView="catalog" />}>
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.catalog.title")}</h2>
        <p className="status-text">{t("modelOps.catalog.description")}</p>
        <ModelCatalogFilters
          search={search}
          taskFilter={taskFilter}
          hostingFilter={hostingFilter}
          stateFilter={stateFilter}
          onSearchChange={setSearch}
          onTaskFilterChange={setTaskFilter}
          onHostingFilterChange={setHostingFilter}
          onStateFilterChange={setStateFilter}
        />
      </article>
      {isLoading ? (
        <p className="status-text">{t("modelOps.states.loading")}</p>
      ) : (
        <ModelCatalogList
          models={filteredModels}
          emptyLabel={t("modelOps.catalog.empty")}
          detailLabel={t("modelOps.actions.openDetail")}
          testLabel={t("modelOps.actions.testModel")}
          validatedLabel={t("modelOps.catalog.validatedBadge")}
          notValidatedLabel={t("modelOps.catalog.notValidatedBadge")}
          canTest={canTest}
        />
      )}
      {error && <p className="error-text">{error}</p>}
    </ModelOpsWorkspaceFrame>
  );
}
