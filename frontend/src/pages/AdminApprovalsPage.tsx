import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";

export default function AdminApprovalsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { activatePendingUser } = useAuth();

  const [userId, setUserId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError("");
    setSuccess("");

    const parsed = Number(userId);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setError(t("auth.approvals.invalidId"));
      return;
    }

    setIsSubmitting(true);
    try {
      const activated = await activatePendingUser(parsed);
      setSuccess(t("auth.approvals.success", { username: activated.username, role: activated.role }));
      setUserId("");
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("auth.approvals.title")}</h2>
      <p className="status-text">{t("auth.approvals.subtitle")}</p>
      <p className="status-text">{t("auth.approvals.note")}</p>

      <form className="card-stack" onSubmit={onSubmit}>
        <label className="control-group">
          <span className="field-label">{t("auth.approvals.userId")}</span>
          <input
            className="field-input"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            placeholder={t("auth.approvals.userIdPlaceholder")}
            inputMode="numeric"
          />
        </label>

        {error && <p className="status-text error-text">{error}</p>}
        {success && <p className="status-text success-text">{success}</p>}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("auth.approvals.submitting") : t("auth.approvals.submit")}
          </button>
        </div>
      </form>
    </section>
  );
}
