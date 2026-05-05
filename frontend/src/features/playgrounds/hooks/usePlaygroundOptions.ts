import { useEffect, useMemo, useState } from "react";
import {
  getPlaygroundKnowledgeBaseOptions,
  getPlaygroundModelOptions,
} from "../../../api/playgrounds";
import type { PlaygroundWorkspaceConfig, PlaygroundWorkspaceOptions } from "../types";
import { hasSelector } from "../selectorConfig";

type UsePlaygroundOptionsParams = {
  token: string;
  isAuthenticated: boolean;
  config: PlaygroundWorkspaceConfig;
};

function buildEmptyOptions(config: PlaygroundWorkspaceConfig): PlaygroundWorkspaceOptions {
  return {
    models: [],
    assistants: [],
    knowledgeBases: [],
    defaultAssistantRef: config.defaultAssistantRef ?? null,
    defaultKnowledgeBaseId: null,
    configurationMessage: "",
  };
}

export function usePlaygroundOptions({ token, isAuthenticated, config }: UsePlaygroundOptionsParams) {
  const hasKnowledgeBaseSelector = hasSelector(config, "knowledgeBase");
  const [options, setOptions] = useState<PlaygroundWorkspaceOptions>(() => buildEmptyOptions(config));
  const [modelError, setModelError] = useState("");
  const [knowledgeBaseError, setKnowledgeBaseError] = useState("");
  const [isModelsLoading, setIsModelsLoading] = useState(false);
  const [hasLoadedModels, setHasLoadedModels] = useState(false);
  const [isKnowledgeBasesLoading, setIsKnowledgeBasesLoading] = useState(false);
  const [hasLoadedKnowledgeBases, setHasLoadedKnowledgeBases] = useState(!hasKnowledgeBaseSelector);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setOptions(buildEmptyOptions(config));
      setModelError("");
      setKnowledgeBaseError("");
      setIsModelsLoading(false);
      setHasLoadedModels(false);
      setIsKnowledgeBasesLoading(false);
      setHasLoadedKnowledgeBases(!hasKnowledgeBaseSelector);
      return;
    }

    let cancelled = false;
    const loadModels = async (): Promise<void> => {
      setIsModelsLoading(true);
      setHasLoadedModels(false);
      try {
        const payload = await getPlaygroundModelOptions(config.playgroundKind, token);
        if (cancelled) {
          return;
        }
        setOptions((current) => ({
          ...current,
          models: payload.models.map((model) => ({
            id: model.id,
            displayName: model.display_name,
          })),
          assistants: payload.assistants,
          defaultAssistantRef: config.defaultAssistantRef ?? payload.assistants[0]?.assistant_ref ?? null,
        }));
        setModelError("");
      } catch (requestError) {
        if (!cancelled) {
          setModelError(requestError instanceof Error ? requestError.message : config.feedback.optionsError);
        }
      } finally {
        if (!cancelled) {
          setIsModelsLoading(false);
          setHasLoadedModels(true);
        }
      }
    };

    void loadModels();
    return () => {
      cancelled = true;
    };
  }, [
    config.defaultAssistantRef,
    config.feedback.optionsError,
    config.playgroundKind,
    hasKnowledgeBaseSelector,
    isAuthenticated,
    token,
  ]);

  useEffect(() => {
    if (!hasKnowledgeBaseSelector) {
      setOptions((current) => ({
        ...current,
        knowledgeBases: [],
        defaultKnowledgeBaseId: null,
        configurationMessage: "",
      }));
      setKnowledgeBaseError("");
      setIsKnowledgeBasesLoading(false);
      setHasLoadedKnowledgeBases(true);
      return;
    }

    if (!isAuthenticated || !token) {
      setOptions((current) => ({
        ...current,
        knowledgeBases: [],
        defaultKnowledgeBaseId: null,
        configurationMessage: "",
      }));
      setKnowledgeBaseError("");
      setIsKnowledgeBasesLoading(false);
      setHasLoadedKnowledgeBases(false);
      return;
    }

    let cancelled = false;
    const loadKnowledgeBases = async (): Promise<void> => {
      setIsKnowledgeBasesLoading(true);
      setHasLoadedKnowledgeBases(false);
      try {
        const payload = await getPlaygroundKnowledgeBaseOptions(token);
        if (cancelled) {
          return;
        }
        const hasExplicitDefaultKnowledgeBase = Object.prototype.hasOwnProperty.call(payload, "default_knowledge_base_id");
        setOptions((current) => ({
          ...current,
          knowledgeBases: payload.knowledge_bases,
          defaultKnowledgeBaseId: hasExplicitDefaultKnowledgeBase
            ? (payload.default_knowledge_base_id ?? null)
            : (payload.knowledge_bases[0]?.id ?? null),
          configurationMessage: payload.configuration_message ?? "",
        }));
        setKnowledgeBaseError("");
      } catch (requestError) {
        if (!cancelled) {
          setKnowledgeBaseError(requestError instanceof Error ? requestError.message : config.feedback.optionsError);
        }
      } finally {
        if (!cancelled) {
          setIsKnowledgeBasesLoading(false);
          setHasLoadedKnowledgeBases(true);
        }
      }
    };

    void loadKnowledgeBases();
    return () => {
      cancelled = true;
    };
  }, [config.feedback.optionsError, hasKnowledgeBaseSelector, isAuthenticated, token]);

  return useMemo(() => {
    const hasLoaded = hasLoadedModels && hasLoadedKnowledgeBases;
    const isLoading = isModelsLoading || isKnowledgeBasesLoading;
    return {
      ...options,
      error: modelError || knowledgeBaseError,
      modelError,
      knowledgeBaseError,
      isLoading,
      hasLoaded,
      isModelsLoading,
      hasLoadedModels,
      isKnowledgeBasesLoading,
      hasLoadedKnowledgeBases,
    };
  }, [
    hasLoadedKnowledgeBases,
    hasLoadedModels,
    isKnowledgeBasesLoading,
    isModelsLoading,
    knowledgeBaseError,
    modelError,
    options,
  ]);
}
