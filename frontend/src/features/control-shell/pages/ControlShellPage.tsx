import { useTranslation } from "react-i18next";
import OptionCardGrid from "../../../components/OptionCardGrid";
import { useAuth } from "../../../auth/AuthProvider";
import { hasRequiredRole } from "../../../auth/roles";
import { controlCardDefinitions } from "../controlItems";

export default function ControlShellPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const currentRole = user?.role ?? "user";
  const displayName = user?.username ?? user?.email ?? t("app.title");

  const visibleItems = controlCardDefinitions
    .filter((item) => hasRequiredRole(currentRole, item.minimumRole))
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      to: item.to,
      icon: item.icon,
    }));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("control.title", { username: displayName })}</h2>
      <p className="status-text">{t("control.description")}</p>
      <OptionCardGrid items={visibleItems} ariaLabel={t("control.aria")} />
    </section>
  );
}
