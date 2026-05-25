import { useTranslation } from "react-i18next";
import type { CatalogExecutionTraceEntry } from "../../../api/catalogExecutionTrace";
import { runtimeDetailRows } from "../catalogExecutionTrace";

type CatalogRuntimeLogProps = {
  entries: CatalogExecutionTraceEntry[];
};

function badgeToneForLevel(level: string): "enabled" | "pending" | "required" {
  if (level === "error") {
    return "required";
  }
  if (level === "warning") {
    return "pending";
  }
  return "enabled";
}

function humanizeDetailKey(key: string): string {
  return key.replace(/_/g, " ");
}

export default function CatalogRuntimeLog({ entries }: CatalogRuntimeLogProps): JSX.Element | null {
  const { t } = useTranslation("common");
  if (!entries.length) {
    return null;
  }

  return (
    <div className="card-stack">
      <span className="field-label">{t("catalogControl.tools.runtimeLogTitle")}</span>
      <div className="catalog-tool-runtime-log" data-testid="catalog-tool-runtime-log">
        {entries.map((entry, index) => {
          const detailRows = runtimeDetailRows(entry.details);
          return (
            <div key={`${entry.stage}-${index}`} className="catalog-tool-runtime-log-entry" data-level={entry.level}>
              <div className="status-row">
                <strong>{entry.message}</strong>
                <span className="platform-badge" data-tone={badgeToneForLevel(entry.level)}>
                  {entry.stage}
                </span>
              </div>
              {detailRows.length ? (
                <dl className="catalog-tool-runtime-log-details">
                  {detailRows.map((row) => (
                    <div key={row.key} className="catalog-tool-runtime-log-detail">
                      <dt>{humanizeDetailKey(row.key)}</dt>
                      <dd>{row.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
