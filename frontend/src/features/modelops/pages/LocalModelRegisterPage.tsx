import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import type { HfModelDetails } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import { TASK_OPTIONS } from "../domain";
import HfModelDetailModal from "../components/HfModelDetailModal";
import LocalArtifactsPanel from "../components/LocalArtifactsPanel";
import LocalDiscoveryPanel from "../components/LocalDiscoveryPanel";
import LocalDownloadsPanel from "../components/LocalDownloadsPanel";
import LocalManualRegistrationPanel from "../components/LocalManualRegistrationPanel";
import { useHfDiscovery } from "../hooks/useHfDiscovery";
import { useLocalDownloadJobs } from "../hooks/useLocalDownloadJobs";

type LocalModelRegisterView = "discovery" | "downloads" | "manual" | "artifacts";

const LOCAL_MODEL_REGISTER_VIEW_ORDER: ReadonlyArray<LocalModelRegisterView> = [
  "discovery",
  "downloads",
  "manual",
  "artifacts",
];

function resolveLocalModelRegisterView(value: string | null): LocalModelRegisterView {
  if (value === "discovery" || value === "downloads" || value === "manual" || value === "artifacts") {
    return value;
  }
  return "discovery";
}

export default function LocalModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = resolveLocalModelRegisterView(searchParams.get("view"));
  const submenuItems = LOCAL_MODEL_REGISTER_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`modelOps.local.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));
  const {
    discoveredModels,
    completedSearchId,
    completedLoadMoreId,
    latestLoadedBatchStartIndex,
    canLoadMoreModels,
    isLoadingMoreModels,
    feedback,
    search,
    loadMore,
    inspect,
  } =
    useHfDiscovery(token);
  const {
    downloadJobs,
    hasActiveJobs,
    download,
  } = useLocalDownloadJobs(token);

  const [discoveryTaskKey, setDiscoveryTaskKey] = useState("llm");
  const [discoverQuery, setDiscoverQuery] = useState("");
  const [inspectedHfModel, setInspectedHfModel] = useState<HfModelDetails | null>(null);

  function handleChangeView(view: LocalModelRegisterView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  return (
    <ModelOpsWorkspaceFrame
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("modelOps.local.views.aria")} />}
    >
      <section className="card-stack">
        {activeView === "discovery" ? (
          <LocalDiscoveryPanel
            taskKey={discoveryTaskKey}
            query={discoverQuery}
            feedback={feedback}
            discoveredModels={discoveredModels}
            completedSearchId={completedSearchId}
            completedLoadMoreId={completedLoadMoreId}
            latestLoadedBatchStartIndex={latestLoadedBatchStartIndex}
            canLoadMoreModels={canLoadMoreModels}
            isLoadingMoreModels={isLoadingMoreModels}
            onTaskKeyChange={setDiscoveryTaskKey}
            onQueryChange={setDiscoverQuery}
            onSearch={() => search({ query: discoverQuery, task_key: discoveryTaskKey })}
            onLoadMore={() => loadMore({ query: discoverQuery, task_key: discoveryTaskKey })}
            onInspect={async (sourceId) => {
              const details = await inspect(sourceId);
              if (details) {
                setInspectedHfModel(details);
              }
            }}
            onDownload={(model) => download(
              model,
              discoveryTaskKey,
              TASK_OPTIONS.find((option) => option.value === discoveryTaskKey)?.category,
            )}
          />
        ) : null}

        {activeView === "downloads" ? (
          <LocalDownloadsPanel
            downloadJobs={downloadJobs}
            hasActiveJobs={hasActiveJobs}
          />
        ) : null}

        {activeView === "manual" ? (
          <LocalManualRegistrationPanel token={token} />
        ) : null}

        {activeView === "artifacts" ? (
          <LocalArtifactsPanel token={token} />
        ) : null}
      </section>
      {inspectedHfModel ? (
        <HfModelDetailModal
          model={inspectedHfModel}
          onClose={() => setInspectedHfModel(null)}
        />
      ) : null}
    </ModelOpsWorkspaceFrame>
  );
}
