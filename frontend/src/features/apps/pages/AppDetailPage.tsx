import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import { getApp, type VanessaApp } from "../../../api/apps";
import PlaygroundWorkspace from "../../playgrounds/components/PlaygroundWorkspace";
import type { PlaygroundWorkspaceConfig } from "../../playgrounds/types";

export default function AppDetailPage(): JSX.Element {
  const { appId = "" } = useParams<{ appId: string }>();
  const { token } = useAuth();
  const [app, setApp] = useState<VanessaApp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !appId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    void getApp(appId, token)
      .then((item) => {
        if (!cancelled) {
          setApp(item);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load app.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [appId, token]);

  const config = useMemo<PlaygroundWorkspaceConfig | null>(() => {
    if (!app) {
      return null;
    }
    return {
      playgroundKind: "chat",
      title: app.name,
      panelAriaLabel: `${app.name} app workspace`,
      introText: app.description,
      loadingText: `Loading ${app.name}...`,
      modelLoadingText: "Loading available models...",
      knowledgeBaseLoadingText: "",
      emptyStateText: `Start chatting with ${app.name}.`,
      newSessionLabel: "New app chat",
      emptySessionTitle: app.name,
      temporarySessionLabel: "Temporary chat",
      temporarySessionTitle: "Temporary chat",
      draftPlaceholder: `Message ${app.name}`,
      inlineSelectors: [],
      settingsSelectors: ["model"],
      messaging: {
        mode: "stream",
        submitLabel: "Send",
        busyLabel: "Working...",
        stopLabel: "Stop response",
      },
      actions: {
        rename: true,
        delete: true,
      },
      sessionBootstrap: {
        mode: "saved-first",
        historyLoadingText: `Loading ${app.name} sessions...`,
      },
      prompts: {
        rename: `Rename ${app.name} session`,
        deleteConfirm: "Delete this app session?",
      },
      feedback: {
        createError: "Unable to create app session.",
        updateModelError: "Unable to update app model.",
        updateKnowledgeBaseError: "Unable to update app settings.",
        updateAssistantError: "Unable to update app assistant.",
        renameError: "Unable to rename app session.",
        deleteError: "Unable to delete app session.",
        sendError: "App request failed.",
        optionsError: "Unable to load app options.",
        sessionsError: "Unable to load app sessions.",
        sessionError: "Unable to load app session.",
        missingModel: "Model is required.",
        missingKnowledgeBase: "",
      },
      defaultAssistantRef: app.agent_id,
      fixedAssistantRef: app.agent_id,
    };
  }, [app]);

  if (loading) {
    return <p className="status-text">Loading app...</p>;
  }
  if (error || !config) {
    return <p className="status-text error-text">{error || "App not found."}</p>;
  }
  return <PlaygroundWorkspace config={config} />;
}
