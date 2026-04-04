import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import QuoteOfTheDayCard from "../components/QuoteOfTheDayCard";
import VanessaBrand from "../components/VanessaBrand";

export default function HomePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { isAuthenticated, user } = useAuth();
  const welcomeBrand = (
    <div className="app-brand welcome-page-brand">
      <h1 className="app-brand-title">
        <VanessaBrand
          className="app-brand-display welcome-page-brand-display"
          label={t("app.title")}
          hoverMode="soft-glow"
        />
      </h1>
    </div>
  );

  if (!isAuthenticated) {
    return (
      <section className="panel card-stack">
        {welcomeBrand}
        <h2 className="section-title">{t("home.guest.title")}</h2>
        <p className="status-text">{t("home.guest.description")}</p>
        <div className="toolbar" role="group" aria-label={t("home.guest.actions") }>
          <Link to="/login" className="btn btn-primary">{t("home.guest.login")}</Link>
          <Link to="/register" className="btn btn-secondary">{t("home.guest.register")}</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="panel card-stack">
      {welcomeBrand}
      <h2 className="section-title">{t("home.authenticated.title")}</h2>
      <p className="status-text">
        {t("home.authenticated.description", {
          username: user?.username ?? user?.email ?? t("app.title"),
        })}
      </p>
      <QuoteOfTheDayCard />
      <div className="toolbar" role="group" aria-label={t("home.authenticated.actions") }>
        <Link to="/control" className="btn btn-secondary">{t("home.authenticated.control")}</Link>
        <Link to="/playgrounds" className="btn btn-secondary">{t("home.authenticated.playgrounds")}</Link>
        <Link to="/agent-builder" className="btn btn-secondary">{t("home.authenticated.agentBuilder")}</Link>
      </div>
    </section>
  );
}
