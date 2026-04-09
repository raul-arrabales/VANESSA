import { useTranslation } from "react-i18next";
import { SCHEMA_PROPERTY_TYPES } from "../schemaEditor";
import { KnowledgeBaseChunkingEditor } from "../components/KnowledgeBaseChunkingEditor";
import { useContextKnowledgeBaseCreate } from "../hooks/useContextKnowledgeBaseCreate";

export default function ContextKnowledgeBaseCreatePage(): JSX.Element {
  const { t } = useTranslation("common");
  const {
    slug,
    displayName,
    description,
    schemaText,
    schemaTextError,
    schemaProperties,
    schemaEditorMode,
    schemaProfiles,
    providerOptions,
    selectedProviderId,
    selectedProfileId,
    selectedProfileDescription,
    vectorizationOptions,
    vectorizationLoadError,
    vectorizationOptionsLoading,
    selectedVectorizationMode,
    selectedEmbeddingProviderId,
    selectedEmbeddingResourceId,
    selectedEmbeddingProviderReady,
    selectedEmbeddingProviderNeedsModel,
    selectedEmbeddingProviderUnavailableReason,
    selectedEmbeddingProviderDisplayName,
    chunkingForm,
    selectedEmbeddingChunkingConstraints,
    chunkingInlineErrorMessage,
    providerLoadError,
    profileLoadError,
    providersLoading,
    schemaProfilesLoading,
    saving,
    saveProfileOpen,
    saveProfileSlug,
    saveProfileDisplayName,
    saveProfileDescription,
    saveProfileSaving,
    isCustomProfileDraft,
    showWeaviateSystemFieldsNote,
    canSaveSchemaProfile,
    setSlug,
    setDisplayName,
    setDescription,
    setSchemaEditorMode,
    setSchemaText,
    setSelectedProfileId,
    setSelectedProviderId,
    setSelectedVectorizationMode,
    setSelectedEmbeddingProviderId,
    setSelectedEmbeddingResourceId,
    updateChunkingField,
    setSaveProfileSlug,
    setSaveProfileDisplayName,
    setSaveProfileDescription,
    toggleSaveProfileOpen,
    addSchemaProperty,
    removeSchemaProperty,
    updateSchemaProperty,
    saveCurrentSchemaProfile,
    handleSubmit,
  } = useContextKnowledgeBaseCreate();

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("contextManagement.createTitle")}</h2>
      <p className="status-text">{t("contextManagement.createDescription")}</p>
      {providerLoadError ? <p className="status-text error-text">{providerLoadError}</p> : null}
      <form className="card-stack" onSubmit={(event) => void handleSubmit(event)}>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
          <input className="field-input" value={slug} onChange={(event) => setSlug(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
          <input className="field-input" value={displayName} onChange={(event) => setDisplayName(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
          <textarea className="field-input quote-admin-textarea" value={description} onChange={(event) => setDescription(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.fields.provider")}</span>
          <select
            className="field-input"
            value={selectedProviderId}
            disabled={providersLoading || saving}
            onChange={(event) => setSelectedProviderId(event.currentTarget.value)}
          >
            <option value="">{t("contextManagement.states.selectProvider")}</option>
            {providerOptions.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {`${provider.display_name} (${provider.provider_key})`}
              </option>
            ))}
          </select>
        </label>

        {selectedProviderId ? (
          <section className="panel panel-nested card-stack" aria-labelledby="kb-advanced-settings-title">
            <div className="card-stack">
              <h3 id="kb-advanced-settings-title" className="section-title">
                {t("contextManagement.advancedSettings.title")}
              </h3>
              <p className="status-text">{t("contextManagement.advancedSettings.description")}</p>
            </div>
            {vectorizationLoadError ? <p className="status-text error-text">{vectorizationLoadError}</p> : null}
            {vectorizationOptionsLoading ? <p className="status-text">{t("contextManagement.states.loadingVectorizationOptions")}</p> : null}
            {!vectorizationOptionsLoading && vectorizationOptions ? (
              <div className="card-stack">
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.advancedSettings.vectorizationMode")}</span>
                  <select
                    className="field-input"
                    value={selectedVectorizationMode}
                    onChange={(event) => setSelectedVectorizationMode(event.currentTarget.value as "vanessa_embeddings" | "self_provided")}
                  >
                    {vectorizationOptions.supported_modes.map((mode) => (
                      <option key={mode.mode} value={mode.mode}>
                        {mode.mode === "self_provided"
                          ? t("contextManagement.advancedSettings.selfProvided")
                          : t("contextManagement.advancedSettings.vanessaEmbeddings")}
                      </option>
                    ))}
                  </select>
                </label>

                {selectedVectorizationMode === "vanessa_embeddings" ? (
                  <div className="card-stack">
                    <label className="card-stack">
                      <span className="field-label">{t("contextManagement.advancedSettings.embeddingProvider")}</span>
                      <select
                        className="field-input"
                        value={selectedEmbeddingProviderId}
                        onChange={(event) => setSelectedEmbeddingProviderId(event.currentTarget.value)}
                      >
                        <option value="">{t("contextManagement.states.selectEmbeddingProvider")}</option>
                        {vectorizationOptions.embedding_providers.map((provider) => (
                          <option key={provider.id} value={provider.id}>
                            {`${provider.display_name ?? provider.id} (${provider.provider_key ?? "embeddings"})`}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="card-stack">
                      <span className="field-label">{t("contextManagement.advancedSettings.embeddingModel")}</span>
                      <select
                        className="field-input"
                        value={selectedEmbeddingResourceId}
                        disabled={!selectedEmbeddingProviderId || !selectedEmbeddingProviderReady}
                        onChange={(event) => setSelectedEmbeddingResourceId(event.currentTarget.value)}
                      >
                        <option value="">{t("contextManagement.states.selectEmbeddingResource")}</option>
                        {(vectorizationOptions.embedding_providers.find((provider) => provider.id === selectedEmbeddingProviderId)?.resources ?? []).map((resource) => (
                          <option key={resource.id} value={resource.id}>
                            {resource.display_name ?? resource.id}
                          </option>
                        ))}
                      </select>
                    </label>
                    {selectedEmbeddingProviderNeedsModel && selectedEmbeddingProviderUnavailableReason === "no_embedding_resources" ? (
                      <p className="status-text">
                        {t("contextManagement.advancedSettings.embeddingProviderNotReady", {
                          provider: selectedEmbeddingProviderDisplayName || t("contextManagement.advancedSettings.embeddingProvider"),
                        })}
                      </p>
                    ) : null}
                    {vectorizationOptions.supports_named_vectors ? (
                      <p className="status-text">{t("contextManagement.advancedSettings.namedVectorsNote")}</p>
                    ) : null}
                  </div>
                ) : (
                  <p className="status-text">{t("contextManagement.advancedSettings.selfProvidedWarning")}</p>
                )}

                <KnowledgeBaseChunkingEditor
                  form={chunkingForm}
                  editable
                  showStrategySelector
                  showDescription
                  showUnitLabel
                  constraints={selectedVectorizationMode === "vanessa_embeddings" ? selectedEmbeddingChunkingConstraints : null}
                  showConstraintsHint={selectedVectorizationMode === "vanessa_embeddings"}
                  inlineSafeLimitErrorMessage={selectedVectorizationMode === "vanessa_embeddings" ? chunkingInlineErrorMessage : null}
                  onChangeField={updateChunkingField}
                />
              </div>
            ) : null}
          </section>
        ) : null}

        <section className="context-schema-panel card-stack" aria-labelledby="schema-builder-title">
          <div className="context-schema-header">
            <div className="card-stack">
              <span className="field-label">{t("contextManagement.fields.schema")}</span>
              <p id="schema-builder-title" className="status-text">{t("contextManagement.schema.description")}</p>
            </div>
            <div className="context-schema-mode-toggle" role="tablist" aria-label={t("contextManagement.schema.modeLabel")}>
              <button
                type="button"
                className={`btn ${schemaEditorMode === "profile" ? "btn-primary" : "btn-secondary"}`}
                aria-pressed={schemaEditorMode === "profile"}
                onClick={() => setSchemaEditorMode("profile")}
              >
                {t("contextManagement.schema.profileMode")}
              </button>
              <button
                type="button"
                className={`btn ${schemaEditorMode === "json" ? "btn-primary" : "btn-secondary"}`}
                aria-pressed={schemaEditorMode === "json"}
                onClick={() => setSchemaEditorMode("json")}
              >
                {t("contextManagement.schema.jsonMode")}
              </button>
            </div>
          </div>

          {schemaEditorMode === "profile" ? (
            <div className="card-stack">
              {profileLoadError ? <p className="status-text error-text">{profileLoadError}</p> : null}
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.schema.profile")}</span>
                <select
                  className="field-input"
                  value={selectedProfileId}
                  disabled={schemaProfilesLoading || saving || !selectedProviderId}
                  onChange={(event) => setSelectedProfileId(event.currentTarget.value)}
                >
                  <option value="">{t("contextManagement.states.selectSchemaProfile")}</option>
                  {schemaProfiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {schemaProfilesLoading ? <p className="status-text">{t("contextManagement.states.loadingSchemaProfiles")}</p> : null}
              {!schemaProfilesLoading && selectedProviderId && schemaProfiles.length === 0 ? (
                <p className="status-text">{t("contextManagement.states.noSchemaProfiles")}</p>
              ) : null}
              {selectedProfileDescription ? <p className="status-text">{selectedProfileDescription}</p> : null}
              {isCustomProfileDraft ? <p className="status-text">{t("contextManagement.states.customSchemaDraft")}</p> : null}
              {showWeaviateSystemFieldsNote ? (
                <p className="status-text">{t("contextManagement.states.weaviateSystemFields")}</p>
              ) : null}

              <div className="card-stack">
                {schemaProperties.map((property, index) => (
                  <div key={index} className="context-schema-row">
                    <label className="card-stack">
                      <span className="field-label">{t("contextManagement.schema.propertyName")}</span>
                      <input
                        className="field-input"
                        value={property.name}
                        onChange={(event) => updateSchemaProperty(index, "name", event.currentTarget.value)}
                      />
                    </label>
                    <label className="card-stack">
                      <span className="field-label">{t("contextManagement.schema.propertyType")}</span>
                      <select
                        className="field-input"
                        value={property.data_type}
                        onChange={(event) => updateSchemaProperty(index, "data_type", event.currentTarget.value)}
                      >
                        {SCHEMA_PROPERTY_TYPES.map((propertyType) => (
                          <option key={propertyType} value={propertyType}>
                            {propertyType}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => removeSchemaProperty(index)}
                    >
                      {t("contextManagement.actions.removeProperty")}
                    </button>
                  </div>
                ))}
                <button type="button" className="btn btn-secondary" onClick={addSchemaProperty}>
                  {t("contextManagement.actions.addProperty")}
                </button>
              </div>
            </div>
          ) : (
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.schema.rawJson")}</span>
              <textarea
                className="field-input quote-admin-textarea"
                value={schemaText}
                onChange={(event) => setSchemaText(event.currentTarget.value)}
                placeholder='{"properties":[{"name":"title","data_type":"text"}]}'
              />
            </label>
          )}

          {schemaTextError ? <p className="status-text error-text">{schemaTextError}</p> : null}

          <div className="context-schema-actions">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!canSaveSchemaProfile || saveProfileSaving || !selectedProviderId}
              onClick={() => toggleSaveProfileOpen()}
            >
              {t("contextManagement.actions.saveSchemaProfile")}
            </button>
          </div>

          {saveProfileOpen ? (
            <section className="context-schema-save-panel card-stack">
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.schema.profileSlug")}</span>
                <input className="field-input" value={saveProfileSlug} onChange={(event) => setSaveProfileSlug(event.currentTarget.value)} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.schema.profileDisplayName")}</span>
                <input
                  className="field-input"
                  value={saveProfileDisplayName}
                  onChange={(event) => setSaveProfileDisplayName(event.currentTarget.value)}
                />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
                <textarea
                  className="field-input quote-admin-textarea"
                  value={saveProfileDescription}
                  onChange={(event) => setSaveProfileDescription(event.currentTarget.value)}
                />
              </label>
              <div className="form-actions">
                <button type="button" className="btn btn-primary" disabled={saveProfileSaving} onClick={() => void saveCurrentSchemaProfile()}>
                  {saveProfileSaving ? t("platformControl.actions.saving") : t("contextManagement.actions.confirmSaveSchemaProfile")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => toggleSaveProfileOpen(false)}>
                  {t("platformControl.actions.cancel")}
                </button>
              </div>
            </section>
          ) : null}
        </section>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving || providersLoading || !selectedProviderId}>
            {saving ? t("platformControl.actions.saving") : t("contextManagement.actions.create")}
          </button>
        </div>
      </form>
    </section>
  );
}
