export const CAPABILITY_IMAGE_ANALYSIS = "image_analysis";

export function capabilityRequiresModelResource(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings" || capability === CAPABILITY_IMAGE_ANALYSIS;
}

export function capabilityUsesTaskDefaults(capability: string): boolean {
  return capability === CAPABILITY_IMAGE_ANALYSIS;
}

export function getDeploymentCapabilityMode(capability: string): "model" | "task_model" | "vector" | "none" {
  if (capabilityUsesTaskDefaults(capability)) {
    return "task_model";
  }
  if (capabilityRequiresModelResource(capability)) {
    return "model";
  }
  if (capability === "vector_store") {
    return "vector";
  }
  return "none";
}

export function capabilitySupportsResources(capability: string): boolean {
  return capabilityRequiresModelResource(capability) || capability === "vector_store";
}
