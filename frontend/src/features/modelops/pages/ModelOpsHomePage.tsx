import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import type { OptionCardItem } from "../../../components/OptionCardGrid";
import ModelOpsEntryCards from "../components/ModelOpsEntryCards";
import ModelSummaryCards from "../components/ModelSummaryCards";
import { useModelOpsSummary } from "../hooks/useModelOpsSummary";

export default function ModelOpsHomePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const role = user?.role;
  const { cards, error, isLoading } = useModelOpsSummary(token, role);

  const entryCards = useMemo((): OptionCardItem[] => {
    const items: OptionCardItem[] = [
      {
        id: "catalog",
        title: t("modelOps.home.cards.catalogTitle"),
        description: t("modelOps.home.cards.catalogDescription"),
        to: "/control/models/catalog",
        icon: "models",
      },
      {
        id: "cloud",
        title: t("modelOps.home.cards.cloudTitle"),
        description: t("modelOps.home.cards.cloudDescription"),
        to: "/control/models/cloud/register",
        icon: "models",
      },
    ];

    if (role === "admin" || role === "superadmin") {
      items.push({
        id: "access",
        title: t("modelOps.home.cards.accessTitle"),
        description: t("modelOps.home.cards.accessDescription"),
        to: "/control/models/access",
        icon: "adminPage",
      });
    }

    if (role === "superadmin") {
      items.push(
        {
          id: "local-register",
          title: t("modelOps.home.cards.localTitle"),
          description: t("modelOps.home.cards.localDescription"),
          to: "/control/models/local/register",
          icon: "models",
        },
        {
          id: "artifacts",
          title: t("modelOps.home.cards.artifactsTitle"),
          description: t("modelOps.home.cards.artifactsDescription"),
          to: "/control/models/local/artifacts",
          icon: "models",
        },
      );
    }

    return items;
  }, [role, t]);

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.home.title")}</h2>
        <p className="status-text">
          {role === "superadmin" ? t("modelOps.home.superadminDescription") : t("modelOps.home.description")}
        </p>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.home.summaryTitle")}</h2>
        {isLoading ? <p className="status-text">{t("modelOps.states.loading")}</p> : <ModelSummaryCards items={cards} />}
        {error && <p className="error-text">{error}</p>}
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.home.entryTitle")}</h2>
        <ModelOpsEntryCards items={entryCards} ariaLabel={t("modelOps.home.entryAria")} />
      </article>
    </section>
  );
}
