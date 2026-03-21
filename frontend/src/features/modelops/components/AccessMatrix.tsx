import type { ManagedModel } from "../../../api/models";

type AccessMatrixProps = {
  scopes: readonly string[];
  models: ManagedModel[];
  assignmentByScope: Map<string, string[]>;
  onToggle: (scope: string, modelId: string) => Promise<void>;
  highlightedModelId?: string;
};

export default function AccessMatrix({
  scopes,
  models,
  assignmentByScope,
  onToggle,
  highlightedModelId,
}: AccessMatrixProps): JSX.Element {
  return (
    <div className="card-stack">
      {scopes.map((scope) => (
        <section key={scope} className="panel card-stack" aria-label={`${scope} access scope`}>
          <h2 className="section-title">{`${scope} scope`}</h2>
          {models.length === 0 ? (
            <p className="status-text">No models available.</p>
          ) : (
            <ul className="card-stack" aria-label={`${scope} access list`}>
              {models.map((model) => {
                const checked = (assignmentByScope.get(scope) ?? []).includes(model.id);
                const isHighlighted = highlightedModelId === model.id;
                return (
                  <li key={`${scope}-${model.id}`} className={`status-row${isHighlighted ? " is-highlighted" : ""}`}>
                    <label className="status-row">
                      <input type="checkbox" checked={checked} onChange={() => void onToggle(scope, model.id)} />
                      <span>{`${model.name} · ${model.task_key ?? "unknown"} · ${model.lifecycle_state ?? "unknown"}`}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}
