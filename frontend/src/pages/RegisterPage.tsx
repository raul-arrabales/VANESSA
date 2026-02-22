import { type FormEvent, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";
import type { Role } from "../auth/types";

const roleOptions: Role[] = ["user", "admin", "superadmin"];

export default function RegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { register, user } = useAuth();

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const canSetRole = useMemo(() => user?.role === "admin" || user?.role === "superadmin", [user]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError("");
    setSuccessMessage("");
    setIsSubmitting(true);

    try {
      const created = await register({
        email,
        username,
        password,
        role: canSetRole ? role : undefined,
      });

      if (created.is_active) {
        setSuccessMessage(t("auth.register.successActive"));
      } else {
        setSuccessMessage(t("auth.register.successPending"));
      }

      setEmail("");
      setUsername("");
      setPassword("");
      setRole("user");
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
      <h2 className="section-title">{t("auth.register.title")}</h2>
      <p className="status-text">{t("auth.register.subtitle")}</p>

      <form className="card-stack" onSubmit={onSubmit}>
        <label className="control-group">
          <span className="field-label">{t("auth.register.email")}</span>
          <input
            className="field-input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>

        <label className="control-group">
          <span className="field-label">{t("auth.register.username")}</span>
          <input
            className="field-input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className="control-group">
          <span className="field-label">{t("auth.register.password")}</span>
          <input
            className="field-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
          />
        </label>

        {canSetRole && (
          <label className="control-group">
            <span className="field-label">{t("auth.register.role")}</span>
            <select className="field-input" value={role} onChange={(event) => setRole(event.target.value as Role)}>
              {roleOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
        )}

        {!canSetRole && <p className="status-text">{t("auth.register.pendingNote")}</p>}
        {error && <p className="status-text error-text">{error}</p>}
        {successMessage && <p className="status-text success-text">{successMessage}</p>}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("auth.register.submitting") : t("auth.register.submit")}
          </button>
        </div>
      </form>
    </section>
  );
}
