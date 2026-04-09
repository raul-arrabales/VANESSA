import { useEffect, useMemo, useState } from "react";
import { EDITABLE_COLOR_TOKENS, type ThemeColors } from "../theme/theme";
import { useTheme } from "../theme/ThemeProvider";

const spacingTokens = ["--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6"] as const;
const radiusTokens = ["--radius-sm", "--radius-md", "--radius-lg"] as const;
const shadowTokens = ["--shadow-1", "--shadow-2", "--shadow-3"] as const;

export default function StyleGuidePage(): JSX.Element {
  const {
    theme,
    themePreset,
    colorOverrides,
    getEffectiveColors,
    applyColorOverrides,
    resetColorOverrides,
  } = useTheme();
  const activeThemeColors = useMemo<ThemeColors>(() => getEffectiveColors(theme), [getEffectiveColors, theme]);

  const [draftColors, setDraftColors] = useState<ThemeColors>(activeThemeColors);

  useEffect(() => {
    setDraftColors(activeThemeColors);
  }, [activeThemeColors, theme, colorOverrides]);

  const isDirty = useMemo(
    () => EDITABLE_COLOR_TOKENS.some((token) => draftColors[token] !== activeThemeColors[token]),
    [activeThemeColors, draftColors],
  );

  const handleColorChange = (token: string, color: string): void => {
    setDraftColors((current) => ({
      ...current,
      [token]: color,
    }));
  };

  const applyThemeChanges = (): void => {
    applyColorOverrides(Object.fromEntries(EDITABLE_COLOR_TOKENS.map((token) => [token, draftColors[token]])));
  };

  const resetThemeChanges = (): void => {
    resetColorOverrides();
  };

  return (
    <section className="style-guide card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">Theme color editor</h2>
        <p className="status-text">Update design token colors for the active preset, {themePreset.id}, and apply them instantly.</p>
        <div className="token-grid token-grid-editor">
          {EDITABLE_COLOR_TOKENS.map((token) => (
            <label key={token} className="token-card token-card-editor">
              <div className="token-swatch" style={{ backgroundColor: draftColors[token] }} aria-hidden="true" />
              <code className="code-inline">{token}</code>
              <input
                className="field-input"
                type="color"
                value={draftColors[token]}
                onChange={(event) => handleColorChange(token, event.target.value)}
                aria-label={`${token} color`}
              />
              <input
                className="field-input"
                type="text"
                value={draftColors[token]}
                onChange={(event) => handleColorChange(token, event.target.value)}
                aria-label={`${token} hex value`}
              />
            </label>
          ))}
        </div>
        <div className="button-row">
          <button className="btn btn-primary" type="button" onClick={applyThemeChanges} disabled={!isDirty}>Apply theme changes</button>
          <button className="btn btn-secondary" type="button" onClick={resetThemeChanges}>Reset current theme</button>
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Typography</h2>
        <p className="type-specimen heading">Heading specimen: NCC-1701 mission control</p>
        <p className="type-specimen body">Body specimen: human-readable operational copy optimized for long sessions.</p>
        <p className="type-specimen mono"><code className="code-inline">Monospace specimen: await engine.health()</code></p>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Panel hierarchy</h2>
        <p className="status-text">
          Use the left rail only on the highest-level page or workspace panel. Nested sections inside that panel should use
          <code className="code-inline"> panel panel-nested</code>
          {" "}
          so the rail does not repeat.
        </p>
        <div className="panel panel-nested card-stack" data-testid="nested-panel-example">
          <h3 className="section-title">Nested panel example</h3>
          <p className="status-text">Nested panels keep the shared surface styling without repeating the left rail decoration.</p>
        </div>
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
        <h2 className="section-title">Primitives preview</h2>
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
