const colorTokens = [
  "--bg-canvas",
  "--bg-surface",
  "--bg-subtle",
  "--text-primary",
  "--text-secondary",
  "--accent-primary",
  "--accent-secondary",
  "--border-muted",
  "--status-success",
  "--status-error",
  "--lcars-rail",
] as const;

const spacingTokens = ["--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6"] as const;
const radiusTokens = ["--radius-sm", "--radius-md", "--radius-lg"] as const;
const shadowTokens = ["--shadow-1", "--shadow-2", "--shadow-3"] as const;

export default function StyleGuidePage(): JSX.Element {
  return (
    <section className="style-guide card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">Color Tokens</h2>
        <p className="status-text">Semantic roles only. Components should never hardcode hex values.</p>
        <div className="token-grid">
          {colorTokens.map((token) => (
            <div key={token} className="token-card">
              <div className="token-swatch" style={{ backgroundColor: `var(${token})` }} aria-hidden="true" />
              <code className="code-inline">{token}</code>
            </div>
          ))}
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Typography</h2>
        <p className="type-specimen heading">Heading specimen: NCC-1701 mission control</p>
        <p className="type-specimen body">Body specimen: human-readable operational copy optimized for long sessions.</p>
        <p className="type-specimen mono"><code className="code-inline">Monospace specimen: await engine.health()</code></p>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Spacing / Radius / Shadow</h2>
        <div className="token-row">
          {spacingTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
        <div className="token-row">
          {radiusTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
        <div className="token-row">
          {shadowTokens.map((token) => <code className="code-inline" key={token}>{token}</code>)}
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Primitives</h2>
        <div className="button-row">
          <button className="btn btn-primary" type="button">Primary</button>
          <button className="btn btn-secondary" type="button">Secondary</button>
          <button className="btn btn-ghost" type="button">Ghost</button>
          <button className="btn btn-primary" type="button" disabled>Disabled</button>
        </div>

        <div className="form-grid">
          <label className="control-group">
            <span className="field-label">Input</span>
            <input className="field-input" placeholder="Search logs" />
          </label>
          <label className="control-group">
            <span className="field-label">Select</span>
            <select className="field-input" defaultValue="active">
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </label>
          <label className="control-group">
            <span className="field-label">Textarea</span>
            <textarea className="field-input" rows={3} placeholder="Operator notes" />
          </label>
        </div>

        <div className="status-demo">
          <span className="status-pill" data-state="success">SUCCESS</span>
          <span className="status-pill" data-state="error">ERROR</span>
        </div>
      </article>
    </section>
  );
}
