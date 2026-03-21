type ModelCatalogFiltersProps = {
  search: string;
  taskFilter: string;
  hostingFilter: string;
  stateFilter: string;
  onSearchChange: (value: string) => void;
  onTaskFilterChange: (value: string) => void;
  onHostingFilterChange: (value: string) => void;
  onStateFilterChange: (value: string) => void;
};

export default function ModelCatalogFilters({
  search,
  taskFilter,
  hostingFilter,
  stateFilter,
  onSearchChange,
  onTaskFilterChange,
  onHostingFilterChange,
  onStateFilterChange,
}: ModelCatalogFiltersProps): JSX.Element {
  return (
    <div className="modelops-filter-grid">
      <label className="card-stack">
        <span className="field-label">Search</span>
        <input className="field-input" value={search} onChange={(event) => onSearchChange(event.currentTarget.value)} />
      </label>
      <label className="card-stack">
        <span className="field-label">Task</span>
        <select className="field-input" value={taskFilter} onChange={(event) => onTaskFilterChange(event.currentTarget.value)}>
          <option value="">All</option>
          <option value="llm">LLM</option>
          <option value="embeddings">Embeddings</option>
          <option value="translation">Translation</option>
          <option value="classification">Classification</option>
        </select>
      </label>
      <label className="card-stack">
        <span className="field-label">Hosting</span>
        <select className="field-input" value={hostingFilter} onChange={(event) => onHostingFilterChange(event.currentTarget.value)}>
          <option value="">All</option>
          <option value="local">Local</option>
          <option value="cloud">Cloud</option>
        </select>
      </label>
      <label className="card-stack">
        <span className="field-label">Lifecycle</span>
        <select className="field-input" value={stateFilter} onChange={(event) => onStateFilterChange(event.currentTarget.value)}>
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="registered">Registered</option>
          <option value="inactive">Inactive</option>
          <option value="unregistered">Unregistered</option>
          <option value="created">Created</option>
        </select>
      </label>
    </div>
  );
}
