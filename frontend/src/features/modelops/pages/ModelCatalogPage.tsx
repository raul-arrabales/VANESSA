import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ModelCatalogFilters from "../components/ModelCatalogFilters";
import ModelCatalogList from "../components/ModelCatalogList";
import { useModelCatalog } from "../hooks/useModelCatalog";
import { useAuth } from "../../../auth/AuthProvider";
import { canAccessModelTesting } from "../permissions";

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
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.catalog.title")}</h2>
        <p className="status-text">{t("modelOps.catalog.description")}</p>
      </article>
      <article className="panel card-stack">
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
          canTest={canTest}
        />
      )}
      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
