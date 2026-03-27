import { useEffect, useMemo, useState } from "react";
import { getPlaygroundOptions } from "../../../api/playgrounds";
import type { PlaygroundWorkspaceConfig, PlaygroundWorkspaceOptions } from "../types";

type UsePlaygroundOptionsParams = {
  token: string;
  isAuthenticated: boolean;
  config: PlaygroundWorkspaceConfig;
};

export function usePlaygroundOptions({ token, isAuthenticated, config }: UsePlaygroundOptionsParams) {
  const [options, setOptions] = useState<PlaygroundWorkspaceOptions>({
    models: [],
    assistants: [],
    knowledgeBases: [],
    defaultAssistantRef: config.defaultAssistantRef ?? null,
    defaultKnowledgeBaseId: null,
    configurationMessage: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setOptions({
        models: [],
        assistants: [],
        knowledgeBases: [],
        defaultAssistantRef: config.defaultAssistantRef ?? null,
        defaultKnowledgeBaseId: null,
        configurationMessage: "",
      });
      setError("");
      setIsLoading(false);
      setHasLoaded(false);
      return;
    }

    let cancelled = false;
    const load = async (): Promise<void> => {
      setIsLoading(true);
      setHasLoaded(false);
      try {
        const payload = await getPlaygroundOptions(token);
        if (cancelled) {
          return;
        }
        const assistants = payload.assistants.filter((assistant) => assistant.playground_kind === config.playgroundKind);
        setOptions({
          models: payload.models.map((model) => ({
            id: model.id,
            displayName: model.display_name,
          })),
          assistants,
          knowledgeBases: payload.knowledge_bases,
          defaultAssistantRef: config.defaultAssistantRef ?? assistants[0]?.assistant_ref ?? null,
          defaultKnowledgeBaseId: payload.default_knowledge_base_id ?? payload.knowledge_bases[0]?.id ?? null,
          configurationMessage: payload.configuration_message ?? "",
        });
        setError("");
        setHasLoaded(true);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : config.feedback.optionsError);
          setHasLoaded(true);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [config.defaultAssistantRef, config.feedback.optionsError, config.playgroundKind, isAuthenticated, token]);

  return useMemo(() => ({
    ...options,
    error,
    isLoading,
    hasLoaded,
  }), [error, hasLoaded, isLoading, options]);
}
