import { ApiError } from "../../auth/authApi";

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function providerName(provider: unknown): string {
  if (!isRecord(provider)) {
    return "Provider";
  }
  return String(provider.display_name || provider.slug || provider.id || "Provider");
}

function failureMessage(failure: unknown): string {
  if (!isRecord(failure)) {
    return "";
  }
  const message = typeof failure.message === "string" ? failure.message.trim() : "";
  if (message) {
    return message;
  }
  const code = typeof failure.code === "string" ? failure.code.trim() : "";
  return code ? code.replace(/_/g, " ") : "";
}

function fallbackValidationMessages(validation: Record<string, unknown>): string[] {
  const messages: string[] = [];
  const bindingError = typeof validation.binding_error === "string" ? validation.binding_error.trim() : "";
  if (bindingError) {
    messages.push(bindingError.replace(/_/g, " "));
  }
  const resourceErrors = Array.isArray(validation.resource_errors) ? validation.resource_errors : [];
  for (const item of resourceErrors) {
    const message = failureMessage(item);
    if (message) {
      messages.push(message);
    }
  }
  if (validation.operation_reachable === false) {
    messages.push("operation check failed");
  }
  if (messages.length === 0 && validation.diagnostic_health_reachable === false) {
    const health = isRecord(validation.health) ? validation.health : {};
    const status = health.status_code ? `HTTP ${String(health.status_code)}` : "health check failed";
    messages.push(status);
  }
  return messages;
}

function providerValidationSummary(item: unknown): string {
  if (!isRecord(item)) {
    return "";
  }
  const validation = isRecord(item.validation) ? item.validation : {};
  const blockingFailures = Array.isArray(validation.blocking_failures) ? validation.blocking_failures : [];
  const messages = blockingFailures
    .map(failureMessage)
    .filter((message) => message.length > 0);
  const effectiveMessages = messages.length > 0 ? messages : fallbackValidationMessages(validation);
  if (effectiveMessages.length === 0) {
    return providerName(item.provider);
  }
  return `${providerName(item.provider)}: ${effectiveMessages.join("; ")}`;
}

export function formatActivationValidationError(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.code !== "deployment_profile_validation_failed") {
    return null;
  }
  const providers = Array.isArray(error.details?.providers) ? error.details.providers : [];
  const summaries = providers
    .map(providerValidationSummary)
    .filter((summary) => summary.length > 0);
  if (summaries.length === 0) {
    return error.message;
  }
  return `${error.message}: ${summaries.join(" ")}`;
}
