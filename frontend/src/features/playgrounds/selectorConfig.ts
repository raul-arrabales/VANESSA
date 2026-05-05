import type { PlaygroundSelectorKind, PlaygroundWorkspaceConfig } from "./types";

export function hasInlineSelector(config: PlaygroundWorkspaceConfig, selector: PlaygroundSelectorKind): boolean {
  return config.inlineSelectors.includes(selector);
}

export function hasSettingsSelector(config: PlaygroundWorkspaceConfig, selector: PlaygroundSelectorKind): boolean {
  return config.settingsSelectors.includes(selector);
}

export function hasSelector(config: PlaygroundWorkspaceConfig, selector: PlaygroundSelectorKind): boolean {
  return hasInlineSelector(config, selector) || hasSettingsSelector(config, selector);
}
