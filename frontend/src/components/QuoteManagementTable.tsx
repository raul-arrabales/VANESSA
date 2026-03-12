import { useTranslation } from "react-i18next";
import type { QuoteAdminItem } from "../api/quoteAdmin";

type QuoteManagementTableProps = {
  items: QuoteAdminItem[];
  total: number;
  page: number;
  totalPages: number;
  isLoading: boolean;
  onSelectQuote: (quoteId: number) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
};

export default function QuoteManagementTable({
  items,
  total,
  page,
  totalPages,
  isLoading,
  onSelectQuote,
  onPreviousPage,
  onNextPage,
}: QuoteManagementTableProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="quote-admin-table-header">
        <h3 className="section-title">{t("quoteAdmin.list.title")}</h3>
        <p className="status-text">{t("quoteAdmin.list.results", { total })}</p>
      </div>

      {isLoading ? (
        <p className="status-text">{t("quoteAdmin.list.loading")}</p>
      ) : items.length === 0 ? (
        <p className="status-text">{t("quoteAdmin.list.empty")}</p>
      ) : (
        <div className="health-table-wrap">
          <table className="health-table" aria-label={t("quoteAdmin.list.tableAria")}>
            <thead>
              <tr>
                <th>{t("quoteAdmin.list.columns.id")}</th>
                <th>{t("quoteAdmin.list.columns.text")}</th>
                <th>{t("quoteAdmin.list.columns.author")}</th>
                <th>{t("quoteAdmin.list.columns.source")}</th>
                <th>{t("quoteAdmin.list.columns.tone")}</th>
                <th>{t("quoteAdmin.list.columns.language")}</th>
                <th>{t("quoteAdmin.list.columns.updated")}</th>
                <th>{t("quoteAdmin.list.columns.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.text}</td>
                  <td>{item.author}</td>
                  <td>{item.source_universe}</td>
                  <td>{item.tone}</td>
                  <td>{item.language}</td>
                  <td>{item.updated_at ?? "--"}</td>
                  <td>
                    <button className="btn btn-ghost" type="button" onClick={() => onSelectQuote(item.id)}>
                      {t("quoteAdmin.actions.edit")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="form-actions">
        <button className="btn btn-ghost" type="button" onClick={onPreviousPage} disabled={page <= 1}>
          {t("quoteAdmin.pagination.previous")}
        </button>
        <p className="status-text">{t("quoteAdmin.pagination.page", { page, totalPages })}</p>
        <button className="btn btn-ghost" type="button" onClick={onNextPage} disabled={page >= totalPages}>
          {t("quoteAdmin.pagination.next")}
        </button>
      </div>
    </article>
  );
}
