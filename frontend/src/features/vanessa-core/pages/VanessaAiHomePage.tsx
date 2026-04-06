import { useTranslation } from "react-i18next";
import OptionCardGrid from "../../../components/OptionCardGrid";

export default function VanessaAiHomePage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("ai.title")}</h2>
      <p className="status-text">{t("ai.description")}</p>
      <OptionCardGrid
        ariaLabel={t("ai.aria")}
        items={[
          {
            id: "vanessa",
            title: t("ai.vanessa.title"),
            description: t("ai.vanessa.description"),
            to: "/ai/vanessa",
            icon: "vanessa",
          },
        ]}
      />
    </section>
  );
}
