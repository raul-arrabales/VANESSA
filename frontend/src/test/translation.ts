import { ensureTestI18n, testI18n } from "./testI18n";

export async function t(key: string, options?: Record<string, unknown>): Promise<string> {
  await ensureTestI18n();
  return testI18n.t(key, options);
}
