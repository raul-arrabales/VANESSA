import { useEffect, useMemo, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import {
  createModelCatalogItem,
  listEnabledModels,
  listModelAssignments,
  listModelCatalog,
  updateModelAssignment,
  type ModelCatalogItem,
  type ModelScopeAssignment,
} from "../api/models";
import LanguageSwitcher from "../components/LanguageSwitcher";
import ProfileSection from "../components/ProfileSection";
import ThemeToggle from "../components/ThemeToggle";

const scopeOrder = ["user", "admin", "superadmin"];

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, token } = useAuth();
  const location = useLocation();

  const isSettingsHome = location.pathname === "/settings";
  const isAdmin = user?.role === "admin" || user?.role === "superadmin";
  const isSuperadmin = user?.role === "superadmin";

  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [enabledModels, setEnabledModels] = useState<ModelCatalogItem[]>([]);
  const [assignments, setAssignments] = useState<ModelScopeAssignment[]>([]);
  const [newModelName, setNewModelName] = useState("");
  const [newModelProvider, setNewModelProvider] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (!token || !user) {
      return;
    }

    const bootstrap = async (): Promise<void> => {
      try {
        const [catalog, assignmentRows, enabled] = await Promise.all([
          listModelCatalog(token),
          isAdmin ? listModelAssignments(token) : Promise.resolve([]),
          listEnabledModels(token),
        ]);
        setModels(catalog);
        setAssignments(assignmentRows);
        setEnabledModels(enabled);
      } catch (error) {
        setFeedback(error instanceof Error ? error.message : "Failed to load model settings.");
      }
    };

    void bootstrap();
  }, [isAdmin, token, user]);

  const assignmentByScope = useMemo(() => {
    const map = new Map<string, string[]>();
    assignments.forEach((assignment) => {
      map.set(assignment.scope, assignment.model_ids);
    });
    return map;
  }, [assignments]);

  const createModel = async (): Promise<void> => {
    if (!token || !newModelName.trim()) {
      return;
    }

    try {
      const created = await createModelCatalogItem(
        {
          name: newModelName.trim(),
          provider: newModelProvider.trim() || undefined,
        },
        token,
      );
      setModels((currentModels) => [...currentModels, created]);
      setNewModelName("");
      setNewModelProvider("");
      setFeedback("Model added to catalog.");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Unable to create model.");
    }
  };

  const toggleAssignment = async (scope: string, modelId: string): Promise<void> => {
    if (!token) {
      return;
    }

    const current = assignmentByScope.get(scope) ?? [];
    const next = current.includes(modelId)
      ? current.filter((id) => id !== modelId)
      : [...current, modelId];

    try {
      const saved = await updateModelAssignment(scope, next, token);
      setAssignments((currentAssignments) => {
        const others = currentAssignments.filter((item) => item.scope !== scope);
        return [...others, saved];
      });
      setFeedback(`Saved ${scope} model assignment.`);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to update model assignments.");
    }
  };

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
      {isSettingsHome && (
        <>
          <ProfileSection titleKey="settings.profile.title" />

          <article className="panel card-stack">
            <h2 className="section-title">Model access</h2>
            <p className="status-text">Enabled models for your account.</p>
            <ul className="card-stack" aria-label="Enabled models list">
              {enabledModels.length > 0 ? (
                enabledModels.map((model) => (
                  <li key={model.id}>{model.name}</li>
                ))
              ) : (
                <li>No models are currently enabled.</li>
              )}
            </ul>
          </article>

          <article className="panel card-stack">
            <h2 className="section-title">{t("settings.user.title")}</h2>
            <p className="status-text">{t("settings.user.description")}</p>
          </article>

          <article className="panel card-stack">
            <h2 className="section-title">{t("settings.personalization.title")}</h2>
            <p className="status-text">{t("settings.personalization.description")}</p>
            <section className="card-stack" aria-label={t("settings.personalization.language.title")}>
              <h3 className="section-title">{t("settings.personalization.language.title")}</h3>
              <p className="status-text">{t("settings.personalization.language.description")}</p>
              <LanguageSwitcher />
            </section>
            <section className="card-stack" aria-label={t("settings.personalization.theme.title")}>
              <h3 className="section-title">{t("settings.personalization.theme.title")}</h3>
              <p className="status-text">{t("settings.personalization.theme.description")}</p>
              <div className="button-row">
                <ThemeToggle />
              </div>
            </section>
          </article>

          {isAdmin && (
            <article className="panel card-stack">
              <h2 className="section-title">{t("settings.admin.title")}</h2>
              <p className="status-text">Assign available models to role scopes.</p>
              <div className="button-row">
                <Link to="/admin/approvals" className="btn btn-secondary">{t("settings.admin.approvals")}</Link>
              </div>
              {scopeOrder.map((scope) => (
                <section key={scope} className="card-stack" aria-label={`${scope} model scope`}>
                  <h3 className="section-title">{scope} scope</h3>
                  {models.length === 0 && <p className="status-text">No models in catalog.</p>}
                  {models.map((model) => {
                    const checked = (assignmentByScope.get(scope) ?? []).includes(model.id);
                    return (
                      <label key={`${scope}-${model.id}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            void toggleAssignment(scope, model.id);
                          }}
                          disabled={!isAdmin}
                        />
                        {` ${model.name}`}
                      </label>
                    );
                  })}
                </section>
              ))}
            </article>
          )}

          {isSuperadmin && (
            <article className="panel card-stack">
              <h2 className="section-title">{t("settings.superadmin.title")}</h2>
              <p className="status-text">Manage the model catalog available to the platform.</p>
              <div className="control-group">
                <label className="field-label" htmlFor="model-name">Model name</label>
                <input
                  id="model-name"
                  className="field-input"
                  value={newModelName}
                  onChange={(event) => setNewModelName(event.currentTarget.value)}
                />
                <label className="field-label" htmlFor="model-provider">Provider</label>
                <input
                  id="model-provider"
                  className="field-input"
                  value={newModelProvider}
                  onChange={(event) => setNewModelProvider(event.currentTarget.value)}
                />
                <button type="button" className="btn btn-primary" onClick={() => void createModel()}>
                  Add model to catalog
                </button>
                <Link to="/settings/design" className="btn btn-secondary">{t("settings.superadmin.styleGuide")}</Link>
              </div>
            </article>
          )}

          {feedback && <p className="status-text">{feedback}</p>}
        </>
      )}
      <Outlet />
    </section>
  );
}
