export function capabilityRequiresModelResource(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
}

export function getDeploymentCapabilityMode(capability: string): "model" | "vector" | "none" {
  if (capabilityRequiresModelResource(capability)) {
    return "model";
  }
  if (capability === "vector_store") {
    return "vector";
  }
  return "none";
}

export function capabilitySupportsResources(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings" || capability === "vector_store";
}
