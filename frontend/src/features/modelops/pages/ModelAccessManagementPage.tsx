import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AccessMatrix from "../components/AccessMatrix";
import { MODEL_ACCESS_SCOPES } from "../constants";
import { useModelAssignments } from "../hooks/useModelAssignments";
import { useAuth } from "../../../auth/AuthProvider";

export default function ModelAccessManagementPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const highlightedModelId = searchParams.get("modelId") ?? undefined;
  const { models, assignmentByScope, error, feedback, isLoading, toggleAssignment } = useModelAssignments(token);
  const [search, setSearch] = useState("");

  const filteredModels = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      return models;
    }
    return models.filter((model) => (
      model.name.toLowerCase().includes(normalized)
      || model.id.toLowerCase().includes(normalized)
      || String(model.task_key ?? "").toLowerCase().includes(normalized)
    ));
  }, [models, search]);

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.access.title")}</h2>
        <p className="status-text">{t("modelOps.access.description")}</p>
        <label className="card-stack">
          <span className="field-label">{t("modelOps.fields.search")}</span>
          <input className="field-input" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
        </label>
      </article>
      {isLoading ? (
        <p className="status-text">{t("modelOps.states.loading")}</p>
      ) : (
        <AccessMatrix
          scopes={MODEL_ACCESS_SCOPES}
          models={filteredModels}
          assignmentByScope={assignmentByScope}
          onToggle={toggleAssignment}
          highlightedModelId={highlightedModelId}
        />
      )}
      {feedback && <p className="status-text">{feedback}</p>}
      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
