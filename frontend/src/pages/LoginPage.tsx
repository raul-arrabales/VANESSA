import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";
import { getDefaultRouteForRole } from "../auth/roles";

export default function LoginPage(): JSX.Element {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const from = (location.state as { from?: string } | null)?.from;

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const user = await login(identifier, password);
      const destination = from || getDefaultRouteForRole(user.role);
      navigate(destination, { replace: true });
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
    <section className="panel card-stack auth-panel">
      <h2 className="section-title">{t("auth.login.title")}</h2>
      <p className="status-text">{t("auth.login.subtitle")}</p>

      <form className="card-stack" onSubmit={onSubmit}>
        <label className="control-group">
          <span className="field-label">{t("auth.login.identifier")}</span>
          <input
            className="field-input"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder={t("auth.login.identifierPlaceholder")}
            autoComplete="username"
            required
          />
        </label>

        <label className="control-group">
          <span className="field-label">{t("auth.login.password")}</span>
          <input
            className="field-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && <p className="status-text error-text">{error}</p>}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("auth.login.submitting") : t("auth.login.submit")}
          </button>
        </div>
      </form>
    </section>
  );
}
