import { useCallback, useEffect, useState } from "react";
import { listModelOpsModels } from "../../../api/modelops/models";
import type { ManagedModel } from "../../../api/modelops/types";

export function useModelCatalog(token: string): {
  models: ManagedModel[];
  isLoading: boolean;
  error: string;
  refresh: () => Promise<void>;
} {
  const [models, setModels] = useState<ManagedModel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      setModels([]);
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      setModels(await listModelOpsModels(token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load models.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { models, isLoading, error, refresh };
}
