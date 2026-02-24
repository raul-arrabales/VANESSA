import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";
import type { AuthUser } from "../auth/types";

export default function AdminApprovalsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, activatePendingUser, listPendingUsers, updateUserRole } = useAuth();

  const [pendingUsers, setPendingUsers] = useState<AuthUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionUserId, setActionUserId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const isSuperadmin = user?.role === "superadmin";

  const loadPendingUsers = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError("");
    try {
      const users = await listPendingUsers();
      setPendingUsers(users);
    } catch (loadError) {
      if (loadError instanceof ApiError) {
        setError(loadError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsLoading(false);
    }
  }, [listPendingUsers, t]);

  useEffect(() => {
    void loadPendingUsers();
  }, [loadPendingUsers]);

  const onActivate = async (targetUser: AuthUser): Promise<void> => {
    setError("");
    setSuccess("");
    setActionUserId(targetUser.id);
    try {
      const activated = await activatePendingUser(targetUser.id);
      setSuccess(t("auth.approvals.success", { username: activated.username, role: activated.role }));
      await loadPendingUsers();
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setActionUserId(null);
    }
  };

  const onPromoteToAdmin = async (targetUser: AuthUser): Promise<void> => {
    setError("");
    setSuccess("");
    setActionUserId(targetUser.id);
    try {
      const updated = await updateUserRole(targetUser.id, "admin");
      setSuccess(t("auth.approvals.promoteSuccess", { username: updated.username }));
      await loadPendingUsers();
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setActionUserId(null);
    }
  };

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("auth.approvals.title")}</h2>
      <p className="status-text">{t("auth.approvals.subtitleWithList")}</p>

      <div className="form-actions">
        <button className="btn btn-ghost" type="button" onClick={() => void loadPendingUsers()} disabled={isLoading}>
          {isLoading ? t("auth.approvals.loading") : t("auth.approvals.refresh")}
        </button>
      </div>

      {error && <p className="status-text error-text">{error}</p>}
      {success && <p className="status-text success-text">{success}</p>}

      {isLoading ? (
        <p className="status-text">{t("auth.approvals.loading")}</p>
      ) : pendingUsers.length === 0 ? (
        <p className="status-text">{t("auth.approvals.empty")}</p>
      ) : (
        <div className="card-stack" role="table" aria-label={t("auth.approvals.tableAria")}>
          {pendingUsers.map((pendingUser) => (
            <article key={pendingUser.id} className="panel card-stack">
              <p className="status-text">#{pendingUser.id} {pendingUser.username} ({pendingUser.email})</p>
              <p className="status-text">{t("auth.approvals.roleLabel", { role: pendingUser.role })}</p>
              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={() => void onActivate(pendingUser)}
                  disabled={actionUserId === pendingUser.id}
                >
                  {actionUserId === pendingUser.id ? t("auth.approvals.submitting") : t("auth.approvals.submit")}
                </button>
                {isSuperadmin && pendingUser.role === "user" && (
                  <button
                    className="btn btn-secondary"
                    type="button"
                    onClick={() => void onPromoteToAdmin(pendingUser)}
                    disabled={actionUserId === pendingUser.id}
                  >
                    {t("auth.approvals.promote")}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
