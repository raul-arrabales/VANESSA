import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";

type ProfileSectionProps = {
  titleKey?: string;
};

export default function ProfileSection({ titleKey = "auth.me.title" }: ProfileSectionProps): JSX.Element {
  const { t } = useTranslation("common");
  const { user, refreshMe, logout } = useAuth();

  if (!user) {
    return (
      <section className="panel card-stack">
        <h2 className="section-title">{t(titleKey)}</h2>
        <p className="status-text">{t("auth.me.missing")}</p>
      </section>
    );
  }

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t(titleKey)}</h2>

      <div className="status-row">
        <span className="field-label">{t("auth.me.email")}</span>
        <code className="code-inline">{user.email}</code>
      </div>

      <div className="status-row">
        <span className="field-label">{t("auth.me.username")}</span>
        <code className="code-inline">{user.username}</code>
      </div>

      <div className="status-row">
        <span className="field-label">{t("auth.me.role")}</span>
        <strong className="status-pill">{user.role.toUpperCase()}</strong>
      </div>

      <div className="status-row">
        <span className="field-label">{t("auth.me.active")}</span>
        <strong className="status-pill" data-state={user.is_active ? "success" : "error"}>
          {user.is_active ? t("auth.me.activeYes") : t("auth.me.activeNo")}
        </strong>
      </div>

      <div className="button-row">
        <button className="btn btn-secondary" type="button" onClick={() => void refreshMe()}>
          {t("auth.me.refresh")}
        </button>
        <button className="btn btn-ghost" type="button" onClick={() => void logout()}>
          {t("auth.logout")}
        </button>
      </div>
    </section>
  );
}
