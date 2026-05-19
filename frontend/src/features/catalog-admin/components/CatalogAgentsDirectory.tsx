import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import ActionIcon from "../../../components/ActionIcon";
import { LifecycleGraphActionModal, useSelectedLifecycleItem } from "../../../components/lifecycle-graph";
import {
  CompactRegistryActions,
  CompactRegistryDescription,
  CompactRegistryHeading,
  CompactRegistryItem,
  CompactRegistryList,
  CompactRegistryMain,
  CompactRegistryMeta,
  CompactRegistryProgress,
} from "../../../components/CompactRegistryList";
import IconButton from "../../../components/IconButton";
import type { CatalogAgent, CatalogAgentValidation } from "../../../api/catalog";
import { createCatalogAgentLifecycleGraphDefinition, getCatalogAgentLifecycleState, getCatalogAgentLifecycleSummaryRows } from "../catalogAgentLifecycleGraph";

type CatalogAgentsDirectoryProps = {
  agents: CatalogAgent[];
  title: string;
  description: string;
  emptyMessage: string;
  validationResults: Record<string, CatalogAgentValidation>;
  validatingAgentId: string;
  deletingAgentId: string;
  onEdit: (agent: CatalogAgent) => void;
  onValidate: (agentId: string) => void;
  onDelete?: (agent: CatalogAgent) => void;
};

type AgentValidationBadge = {
  label: string;
  tone: "active" | "inactive" | "optional" | "required";
};

function getAgentValidationBadge(
  validation: CatalogAgentValidation["validation"] | undefined,
  isValidating: boolean,
  t: TFunction<"common">,
): AgentValidationBadge {
  if (isValidating) {
    return {
      label: t("catalogControl.agents.validationBadges.validating"),
      tone: "optional",
    };
  }
  if (!validation) {
    return {
      label: t("catalogControl.agents.validationBadges.unvalidated"),
      tone: "required",
    };
  }
  return validation.valid
    ? { label: t("catalogControl.agents.validationBadges.validated"), tone: "active" }
    : { label: t("catalogControl.agents.validationBadges.failed"), tone: "inactive" };
}

export default function CatalogAgentsDirectory({
  agents,
  title,
  description,
  emptyMessage,
  validationResults,
  validatingAgentId,
  deletingAgentId,
  onEdit,
  onValidate,
  onDelete,
}: CatalogAgentsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");
  const { selectedLifecycleItem, openLifecycleItem, closeLifecycleItem } = useSelectedLifecycleItem<CatalogAgent>();
  const lifecycleDefinition = useMemo(() => createCatalogAgentLifecycleGraphDefinition(t), [t]);

  return (
    <>
      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{title}</h3>
          <p className="status-text">{description}</p>
        </div>

        <CompactRegistryList>
          {agents.length === 0 ? <p className="status-text">{emptyMessage}</p> : null}
          {agents.map((agent) => {
            const validationResult = validationResults[agent.id];
            const validation = validationResult?.validation;
            const isValidating = validatingAgentId === agent.id;
            const isDeleting = deletingAgentId === agent.id;
            const validationBadge = getAgentValidationBadge(validation, isValidating, t);
            const validateLabel = isValidating
              ? t("catalogControl.agents.actionLabels.validating", { name: agent.spec.name })
              : t("catalogControl.agents.actionLabels.validate", { name: agent.spec.name });
            const deleteLabel = isDeleting
              ? t("catalogControl.agents.actionLabels.deleting", { name: agent.spec.name })
              : t("catalogControl.agents.actionLabels.delete", { name: agent.spec.name });

            return (
              <CompactRegistryItem key={agent.id}>
                <CompactRegistryMain>
                  <CompactRegistryHeading>
                    <h4 className="section-title">{agent.spec.name}</h4>
                    <span className="platform-badge" data-tone={agent.published ? "active" : "required"}>
                      {agent.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                    </span>
                    <span className="platform-badge" data-tone={validationBadge.tone}>
                      {validationBadge.label}
                    </span>
                    {agent.spec.runtime_constraints.internet_required ? (
                      <span className="platform-badge" data-tone="optional">
                        {t("catalogControl.agents.internetRequired")}
                      </span>
                    ) : null}
                    {agent.spec.runtime_constraints.sandbox_required ? (
                      <span className="platform-badge" data-tone="optional">
                        {t("catalogControl.agents.sandboxRequired")}
                      </span>
                    ) : null}
                  </CompactRegistryHeading>
                  <CompactRegistryDescription>{agent.spec.description}</CompactRegistryDescription>
                  <CompactRegistryMeta>
                    <code className="code-inline">{agent.id}</code>
                    <span>{t("catalogControl.summary.version", { version: agent.current_version })}</span>
                    <span>{t("catalogControl.agents.modelLabel", { model: agent.spec.default_model_ref ?? "-" })}</span>
                    <span>{t("catalogControl.agents.toolsLabel", { count: agent.spec.tool_refs.length })}</span>
                    <span>
                      {t("catalogControl.agents.updatedLabel", {
                        updated: agent.updated_at ?? agent.published_at ?? "-",
                      })}
                    </span>
                  </CompactRegistryMeta>
                </CompactRegistryMain>
                <CompactRegistryActions label={t("catalogControl.agents.actionsFor", { name: agent.spec.name })}>
                  <IconButton label={t("catalogControl.agents.actionLabels.lifecycle", { name: agent.spec.name })} onClick={() => openLifecycleItem(agent)}>
                    <ActionIcon name="lifecycle" />
                  </IconButton>
                  <IconButton label={t("catalogControl.agents.actionLabels.edit", { name: agent.spec.name })} onClick={() => onEdit(agent)}>
                    <ActionIcon name="edit" />
                  </IconButton>
                  <IconButton label={validateLabel} onClick={() => onValidate(agent.id)} disabled={isValidating}>
                    <ActionIcon name="validate" />
                  </IconButton>
                  {onDelete ? (
                    <IconButton label={deleteLabel} tone="danger" onClick={() => onDelete(agent)} disabled={isDeleting}>
                      <ActionIcon name="delete" />
                    </IconButton>
                  ) : null}
                </CompactRegistryActions>
                {validation ? (
                  <CompactRegistryProgress>
                    <span className="field-label">
                      {validation.valid ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
                    </span>
                    {validation.errors.length > 0 ? (
                      <ul className="status-text">
                        {validation.errors.map((message) => (
                          <li key={message}>{message}</li>
                        ))}
                      </ul>
                    ) : null}
                  </CompactRegistryProgress>
                ) : null}
              </CompactRegistryItem>
            );
          })}
        </CompactRegistryList>
      </article>

      <LifecycleGraphActionModal
        item={selectedLifecycleItem}
        getTitle={(agent) => t("catalogControl.agents.lifecycle.modalTitle", { name: agent.spec.name })}
        description={t("catalogControl.agents.lifecycle.modalDescription")}
        closeLabel={t("actionFeedback.dialog.close")}
        definition={lifecycleDefinition}
        getCurrentState={(agent) => getCatalogAgentLifecycleState(agent, validationResults[agent.id])}
        getSummaryRows={(agent) => getCatalogAgentLifecycleSummaryRows(t, agent, validationResults[agent.id])}
        currentLabel={t("catalogControl.agents.lifecycle.currentState")}
        unknownLabel={t("catalogControl.agents.lifecycle.states.unknown")}
        onClose={closeLifecycleItem}
      />
    </>
  );
}
