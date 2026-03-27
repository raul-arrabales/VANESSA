import { useTranslation } from "react-i18next";
import { ApiError } from "../../../auth/authApi";
import { useAuth } from "../../../auth/AuthProvider";
import type { AuthUser } from "../../../auth/types";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { useAdminApprovals } from "../hooks/useAdminApprovals";

export default function AdminApprovalsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, token } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const {
    pendingUsers,
    isLoading,
    actionUserId,
    error,
    refreshPendingUsers,
    activateUser,
    promoteUserToAdmin,
  } = useAdminApprovals(token);

  const isSuperadmin = user?.role === "superadmin";

  const onActivate = async (targetUser: AuthUser): Promise<void> => {
    try {
      const activated = await activateUser(targetUser);
      showSuccessFeedback(t("auth.approvals.success", { username: activated.username, role: activated.role }));
      await refreshPendingUsers();
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        showErrorFeedback(submitError, t("auth.error.unknown"));
      } else {
        showErrorFeedback(submitError, t("auth.error.unknown"));
      }
    }
  };

  const onPromoteToAdmin = async (targetUser: AuthUser): Promise<void> => {
    try {
      const updated = await promoteUserToAdmin(targetUser);
      showSuccessFeedback(t("auth.approvals.promoteSuccess", { username: updated.username }));
      await refreshPendingUsers();
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        showErrorFeedback(submitError, t("auth.error.unknown"));
      } else {
        showErrorFeedback(submitError, t("auth.error.unknown"));
      }
    }
  };

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("auth.approvals.title")}</h2>
      <p className="status-text">{t("auth.approvals.subtitleWithList")}</p>

      <div className="form-actions">
        <button className="btn btn-ghost" type="button" onClick={() => void refreshPendingUsers()} disabled={isLoading}>
          {isLoading ? t("auth.approvals.loading") : t("auth.approvals.refresh")}
        </button>
      </div>

      {error && <p className="status-text error-text">{error}</p>}

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
