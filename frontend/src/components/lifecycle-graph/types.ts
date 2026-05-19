export type LifecycleStateDefinition = {
  id: string;
  label: string;
  description?: string;
  x?: number;
  y?: number;
};

export type LifecycleTransitionDefinition = {
  from: string;
  to: string;
  label?: string;
};

export type LifecycleGraphDefinition = {
  artifactType: string;
  states: LifecycleStateDefinition[];
  transitions: LifecycleTransitionDefinition[];
};

export type LifecycleCounts = {
  byState: Record<string, number>;
  unknown: number;
};

export type LifecycleHighlight = {
  currentState: string | null;
  outgoingTransitions: Set<string>;
};

export type LifecycleSummaryRow = {
  label: string;
  value: string | number;
  tone?: "active" | "enabled" | "disabled" | "inactive" | "optional" | "required" | "success" | "warning" | "danger";
};

export type LifecycleGraphProps = {
  definition: LifecycleGraphDefinition;
  counts?: LifecycleCounts;
  currentState?: string | null;
  supportingText?: string;
  summaryRows?: LifecycleSummaryRow[];
  currentLabel?: string;
  unknownLabel?: string;
};

export type LifecycleGraphModalProps = LifecycleGraphProps & {
  title: string;
  description?: string;
  closeLabel: string;
  onClose: () => void;
};

export type LifecycleGraphDefinitionOptions<StateId extends string = string> = {
  artifactType: string;
  stateIds: readonly StateId[];
  i18nBase: string;
  transitions: readonly LifecycleTransitionDefinition[];
  positions?: Partial<Record<StateId, { x: number; y: number }>> | readonly { x: number; y: number }[];
  transitionLabelKey?: (transition: LifecycleTransitionDefinition) => string;
};

export type LifecycleGraphPanelProps<T> = {
  title: string;
  description: string;
  definition: LifecycleGraphDefinition;
  items: T[];
  getState: (item: T) => string | null | undefined;
  currentLabel: string;
  unknownLabel: string;
  titleAs?: "h2" | "h3";
  className?: string;
  headerClassName?: string;
  headerContentClassName?: string;
};

export type LifecycleGraphActionModalProps<T> = Omit<LifecycleGraphModalProps, "title" | "currentState" | "supportingText" | "summaryRows" | "onClose"> & {
  item: T | null;
  getTitle: (item: T) => string;
  getCurrentState: (item: T) => string | null | undefined;
  getSupportingText?: (item: T) => string;
  getSummaryRows?: (item: T) => LifecycleSummaryRow[];
  onClose: () => void;
};
