import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  createKnowledgeBase,
  type KnowledgeBaseChunkingStrategy,
  createKnowledgeBaseSchemaProfile,
  getKnowledgeBaseVectorizationOptions,
  listKnowledgeBaseSchemaProfiles,
  type KnowledgeBaseSchema,
  type KnowledgeBaseSchemaProfile,
  type KnowledgeBaseSchemaProperty,
  type KnowledgeBaseSchemaPropertyType,
  type KnowledgeBaseVectorizationMode,
  type KnowledgeBaseVectorizationOptions,
} from "../../../api/context";
import { listPlatformProviders, type PlatformProvider } from "../../../api/platform";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import {
  buildSchemaFromProperties,
  createDefaultSchemaProperty,
  parseSchemaText,
  schemaPropertiesFromSchema,
  schemaToPrettyJson,
  schemasEqual,
} from "../schemaEditor";

type SchemaEditorMode = "profile" | "json";

type UseContextKnowledgeBaseCreateResult = {
  slug: string;
  displayName: string;
  description: string;
  schemaText: string;
  schemaTextError: string;
  schemaProperties: KnowledgeBaseSchemaProperty[];
  schemaEditorMode: SchemaEditorMode;
  schemaProfiles: KnowledgeBaseSchemaProfile[];
  providerOptions: PlatformProvider[];
  selectedProviderId: string;
  selectedProviderKey: string;
  vectorizationOptions: KnowledgeBaseVectorizationOptions | null;
  vectorizationLoadError: string;
  vectorizationOptionsLoading: boolean;
  selectedVectorizationMode: KnowledgeBaseVectorizationMode;
  selectedEmbeddingProviderId: string;
  selectedEmbeddingResourceId: string;
  selectedEmbeddingProviderReady: boolean;
  selectedEmbeddingProviderNeedsModel: boolean;
  selectedEmbeddingProviderUnavailableReason: string | null;
  selectedEmbeddingProviderDisplayName: string;
  selectedChunkingStrategy: KnowledgeBaseChunkingStrategy;
  chunkLength: string;
  chunkOverlap: string;
  selectedProfileId: string;
  selectedProfileDescription: string;
  providerLoadError: string;
  profileLoadError: string;
  providersLoading: boolean;
  schemaProfilesLoading: boolean;
  saving: boolean;
  saveProfileOpen: boolean;
  saveProfileSlug: string;
  saveProfileDisplayName: string;
  saveProfileDescription: string;
  saveProfileSaving: boolean;
  isCustomProfileDraft: boolean;
  showWeaviateSystemFieldsNote: boolean;
  canSaveSchemaProfile: boolean;
  setSlug: (value: string) => void;
  setDisplayName: (value: string) => void;
  setDescription: (value: string) => void;
  setSelectedProviderId: (value: string) => void;
  setSelectedVectorizationMode: (value: KnowledgeBaseVectorizationMode) => void;
  setSelectedEmbeddingProviderId: (value: string) => void;
  setSelectedEmbeddingResourceId: (value: string) => void;
  setSelectedChunkingStrategy: (value: KnowledgeBaseChunkingStrategy) => void;
  setChunkLength: (value: string) => void;
  setChunkOverlap: (value: string) => void;
  setSchemaEditorMode: (value: SchemaEditorMode) => void;
  setSchemaText: (value: string) => void;
  setSelectedProfileId: (value: string) => void;
  setSaveProfileSlug: (value: string) => void;
  setSaveProfileDisplayName: (value: string) => void;
  setSaveProfileDescription: (value: string) => void;
  toggleSaveProfileOpen: (value?: boolean) => void;
  addSchemaProperty: () => void;
  removeSchemaProperty: (index: number) => void;
  updateSchemaProperty: (index: number, field: "name" | "data_type", value: string) => void;
  saveCurrentSchemaProfile: () => Promise<void>;
  handleSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function useContextKnowledgeBaseCreate(): UseContextKnowledgeBaseCreateResult {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [schemaText, setSchemaTextState] = useState("");
  const [schemaTextError, setSchemaTextError] = useState("");
  const [schemaProperties, setSchemaProperties] = useState<KnowledgeBaseSchemaProperty[]>([]);
  const [schemaProfiles, setSchemaProfiles] = useState<KnowledgeBaseSchemaProfile[]>([]);
  const [providerOptions, setProviderOptions] = useState<PlatformProvider[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [vectorizationOptions, setVectorizationOptions] = useState<KnowledgeBaseVectorizationOptions | null>(null);
  const [vectorizationLoadError, setVectorizationLoadError] = useState("");
  const [vectorizationOptionsLoading, setVectorizationOptionsLoading] = useState(false);
  const [selectedVectorizationMode, setSelectedVectorizationMode] = useState<KnowledgeBaseVectorizationMode>("vanessa_embeddings");
  const [selectedEmbeddingProviderId, setSelectedEmbeddingProviderId] = useState("");
  const [selectedEmbeddingResourceId, setSelectedEmbeddingResourceId] = useState("");
  const [selectedChunkingStrategy, setSelectedChunkingStrategy] = useState<KnowledgeBaseChunkingStrategy>("fixed_length");
  const [chunkLength, setChunkLength] = useState("300");
  const [chunkOverlap, setChunkOverlap] = useState("60");
  const [selectedProfileId, setSelectedProfileIdState] = useState("");
  const [schemaEditorMode, setSchemaEditorMode] = useState<SchemaEditorMode>("profile");
  const [providerLoadError, setProviderLoadError] = useState("");
  const [profileLoadError, setProfileLoadError] = useState("");
  const [providersLoading, setProvidersLoading] = useState(true);
  const [schemaProfilesLoading, setSchemaProfilesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveProfileOpen, setSaveProfileOpen] = useState(false);
  const [saveProfileSlug, setSaveProfileSlug] = useState("");
  const [saveProfileDisplayName, setSaveProfileDisplayName] = useState("");
  const [saveProfileDescription, setSaveProfileDescription] = useState("");
  const [saveProfileSaving, setSaveProfileSaving] = useState(false);

  const enabledVectorProviders = useMemo(
    () => providerOptions.filter((provider) => provider.capability === "vector_store" && provider.enabled),
    [providerOptions],
  );
  const selectedProvider = useMemo(
    () => enabledVectorProviders.find((provider) => provider.id === selectedProviderId) ?? null,
    [enabledVectorProviders, selectedProviderId],
  );
  const selectedProviderKey = selectedProvider?.provider_key ?? "";
  const selectedEmbeddingProvider = useMemo(
    () => vectorizationOptions?.embedding_providers.find((provider) => provider.id === selectedEmbeddingProviderId) ?? null,
    [selectedEmbeddingProviderId, vectorizationOptions],
  );
  const selectedEmbeddingProviderResources = selectedEmbeddingProvider?.resources ?? [];
  const selectedEmbeddingProviderReady = Boolean(selectedEmbeddingProvider?.is_ready ?? selectedEmbeddingProviderResources.length > 0);
  const selectedEmbeddingProviderNeedsModel = Boolean(selectedEmbeddingProviderId) && !selectedEmbeddingProviderReady;
  const selectedProfile = useMemo(
    () => schemaProfiles.find((profile) => profile.id === selectedProfileId) ?? null,
    [schemaProfiles, selectedProfileId],
  );
  const currentSchemaFromProperties = useMemo<KnowledgeBaseSchema>(
    () => buildSchemaFromProperties(schemaProperties),
    [schemaProperties],
  );
  const selectedProfileDescription = selectedProfile?.description ?? "";
  const isCustomProfileDraft = Boolean(
    selectedProfile && !schemasEqual(currentSchemaFromProperties, selectedProfile.schema),
  );
  const showWeaviateSystemFieldsNote = selectedProviderKey === "weaviate_local";
  const canSaveSchemaProfile = Boolean(selectedProviderKey) && !schemaTextError;

  useEffect(() => {
    if (!token) {
      setProvidersLoading(false);
      return;
    }
    const loadProviders = async (): Promise<void> => {
      setProvidersLoading(true);
      setProviderLoadError("");
      try {
        const providers = await listPlatformProviders(token);
        setProviderOptions(providers);
      } catch (requestError) {
        setProviderLoadError(requestError instanceof Error ? requestError.message : t("contextManagement.feedback.providerLoadFailed"));
      } finally {
        setProvidersLoading(false);
      }
    };
    void loadProviders();
  }, [t, token]);

  useEffect(() => {
    if (enabledVectorProviders.length === 1 && !selectedProviderId) {
      setSelectedProviderId(enabledVectorProviders[0].id);
    }
  }, [enabledVectorProviders, selectedProviderId]);

  useEffect(() => {
    if (!token || !selectedProviderKey) {
      setSchemaProfiles([]);
      setProfileLoadError("");
      setSchemaProfilesLoading(false);
      setSelectedProfileIdState("");
      return;
    }
    const loadProfiles = async (): Promise<void> => {
      setSchemaProfilesLoading(true);
      setProfileLoadError("");
      try {
        const profiles = await listKnowledgeBaseSchemaProfiles(selectedProviderKey, token);
        setSchemaProfiles(profiles);
      } catch (requestError) {
        setSchemaProfiles([]);
        setProfileLoadError(requestError instanceof Error ? requestError.message : t("contextManagement.feedback.schemaProfilesLoadFailed"));
      } finally {
        setSchemaProfilesLoading(false);
      }
    };
    void loadProfiles();
  }, [selectedProviderKey, t, token]);

  useEffect(() => {
    if (!token || !selectedProviderId) {
      setVectorizationOptions(null);
      setVectorizationLoadError("");
      setVectorizationOptionsLoading(false);
      setSelectedVectorizationMode("vanessa_embeddings");
      setSelectedEmbeddingProviderId("");
      setSelectedEmbeddingResourceId("");
      return;
    }
    const loadVectorizationOptions = async (): Promise<void> => {
      setVectorizationOptionsLoading(true);
      setVectorizationLoadError("");
      try {
        const options = await getKnowledgeBaseVectorizationOptions(selectedProviderId, token);
        setVectorizationOptions(options);
      } catch (requestError) {
        setVectorizationOptions(null);
        setVectorizationLoadError(
          requestError instanceof Error ? requestError.message : t("contextManagement.feedback.vectorizationOptionsLoadFailed"),
        );
      } finally {
        setVectorizationOptionsLoading(false);
      }
    };
    void loadVectorizationOptions();
  }, [selectedProviderId, t, token]);

  useEffect(() => {
    const supportedModes = (vectorizationOptions?.supported_modes ?? [])
      .map((item) => item.mode)
      .filter((item): item is KnowledgeBaseVectorizationMode => item === "vanessa_embeddings" || item === "self_provided");
    if (supportedModes.length === 0) {
      setSelectedVectorizationMode("vanessa_embeddings");
      return;
    }
    if (!supportedModes.includes(selectedVectorizationMode)) {
      setSelectedVectorizationMode(supportedModes[0]);
    }
  }, [selectedVectorizationMode, vectorizationOptions]);

  useEffect(() => {
    const providers = vectorizationOptions?.embedding_providers ?? [];
    if (providers.length === 0) {
      setSelectedEmbeddingProviderId("");
      setSelectedEmbeddingResourceId("");
      return;
    }
    if (!providers.some((provider) => provider.id === selectedEmbeddingProviderId)) {
      const nextProviderId = providers.length === 1 ? providers[0].id : "";
      setSelectedEmbeddingProviderId(nextProviderId);
      if (!nextProviderId) {
        setSelectedEmbeddingResourceId("");
      }
    }
  }, [selectedEmbeddingProviderId, vectorizationOptions]);

  useEffect(() => {
    if (!selectedEmbeddingProvider) {
      setSelectedEmbeddingResourceId("");
      return;
    }
    const resourceIds = new Set(selectedEmbeddingProviderResources.map((resource) => resource.id));
    if (!resourceIds.has(selectedEmbeddingResourceId)) {
      setSelectedEmbeddingResourceId(
        selectedEmbeddingProvider.default_resource_id
          || selectedEmbeddingProviderResources[0]?.id
          || "",
      );
    }
  }, [selectedEmbeddingProvider, selectedEmbeddingProviderResources, selectedEmbeddingResourceId]);

  useEffect(() => {
    if (selectedProfileId && !schemaProfiles.some((profile) => profile.id === selectedProfileId)) {
      setSelectedProfileIdState("");
    }
    if (schemaProfiles.length === 1 && !selectedProfileId && !schemaText.trim()) {
      const profile = schemaProfiles[0];
      setSelectedProfileIdState(profile.id);
      const properties = schemaPropertiesFromSchema(profile.schema);
      setSchemaProperties(properties);
      setSchemaTextState(schemaToPrettyJson(profile.schema));
      setSchemaTextError("");
    }
  }, [schemaProfiles, schemaText, selectedProfileId]);

  function replaceSchemaProperties(nextProperties: KnowledgeBaseSchemaProperty[]): void {
    setSchemaProperties(nextProperties);
    setSchemaTextState(schemaToPrettyJson(buildSchemaFromProperties(nextProperties)));
    setSchemaTextError("");
  }

  function selectSchemaProfile(profileId: string): void {
    setSelectedProfileIdState(profileId);
    const profile = schemaProfiles.find((item) => item.id === profileId);
    if (!profile) {
      return;
    }
    setSchemaEditorMode("profile");
    setSchemaProperties(schemaPropertiesFromSchema(profile.schema));
    setSchemaTextState(schemaToPrettyJson(profile.schema));
    setSchemaTextError("");
    setSaveProfileOpen(false);
  }

  function setSchemaText(value: string): void {
    setSchemaTextState(value);
    try {
      const parsed = parseSchemaText(value);
      setSchemaProperties(schemaPropertiesFromSchema(parsed));
      setSchemaTextError("");
    } catch {
      setSchemaTextError(t("contextManagement.feedback.invalidSchema"));
    }
  }

  function addSchemaProperty(): void {
    replaceSchemaProperties([...schemaProperties, createDefaultSchemaProperty(schemaProperties.length)]);
  }

  function removeSchemaProperty(index: number): void {
    replaceSchemaProperties(schemaProperties.filter((_, currentIndex) => currentIndex !== index));
  }

  function updateSchemaProperty(index: number, field: "name" | "data_type", value: string): void {
    const nextProperties = schemaProperties.map((property, currentIndex) => {
      if (currentIndex !== index) {
        return property;
      }
      return {
        ...property,
        [field]: field === "data_type"
          ? (value as KnowledgeBaseSchemaPropertyType)
          : value,
      };
    });
    replaceSchemaProperties(nextProperties);
  }

  function toggleSaveProfileOpen(value?: boolean): void {
    const nextValue = value ?? !saveProfileOpen;
    setSaveProfileOpen(nextValue);
    if (!nextValue) {
      return;
    }
    setSaveProfileSlug((current) => current || buildSuggestedProfileSlug(selectedProfile, displayName, slug));
    setSaveProfileDisplayName((current) => current || buildSuggestedProfileDisplayName(selectedProfile, displayName));
    setSaveProfileDescription((current) => current || selectedProfileDescription);
  }

  async function reloadSchemaProfiles(nextSelectedProfileId?: string): Promise<void> {
    if (!token || !selectedProviderKey) {
      return;
    }
    const profiles = await listKnowledgeBaseSchemaProfiles(selectedProviderKey, token);
    setSchemaProfiles(profiles);
    if (nextSelectedProfileId) {
      setSelectedProfileIdState(nextSelectedProfileId);
    }
  }

  async function saveCurrentSchemaProfile(): Promise<void> {
    if (!token || !selectedProviderKey) {
      return;
    }
    let schema: KnowledgeBaseSchema;
    try {
      schema = parseSchemaText(schemaText);
    } catch {
      showErrorFeedback(t("contextManagement.feedback.invalidSchema"), t("contextManagement.feedback.schemaProfileCreateFailed"));
      return;
    }
    if (!saveProfileSlug.trim()) {
      showErrorFeedback(t("contextManagement.feedback.schemaProfileSlugRequired"), t("contextManagement.feedback.schemaProfileCreateFailed"));
      return;
    }
    if (!saveProfileDisplayName.trim()) {
      showErrorFeedback(t("contextManagement.feedback.schemaProfileDisplayNameRequired"), t("contextManagement.feedback.schemaProfileCreateFailed"));
      return;
    }
    setSaveProfileSaving(true);
    try {
      const savedProfile = await createKnowledgeBaseSchemaProfile(
        {
          slug: saveProfileSlug.trim(),
          display_name: saveProfileDisplayName.trim(),
          description: saveProfileDescription.trim(),
          provider_key: selectedProviderKey,
          schema,
        },
        token,
      );
      await reloadSchemaProfiles(savedProfile.id);
      setSelectedProfileIdState(savedProfile.id);
      setSaveProfileOpen(false);
      showSuccessFeedback(t("contextManagement.feedback.schemaProfileCreated", { name: savedProfile.display_name }));
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.schemaProfileCreateFailed"));
    } finally {
      setSaveProfileSaving(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    if (!selectedProviderId) {
      showErrorFeedback(t("contextManagement.feedback.providerRequired"), t("contextManagement.feedback.createFailed"));
      return;
    }
    if (schemaEditorMode === "profile" && schemaProfiles.length > 0 && !selectedProfileId) {
      showErrorFeedback(t("contextManagement.feedback.schemaProfileRequired"), t("contextManagement.feedback.createFailed"));
      return;
    }
    if (selectedVectorizationMode === "vanessa_embeddings" && !selectedEmbeddingProviderId) {
      showErrorFeedback(t("contextManagement.feedback.embeddingProviderRequired"), t("contextManagement.feedback.createFailed"));
      return;
    }
    if (selectedVectorizationMode === "vanessa_embeddings" && !selectedEmbeddingResourceId) {
      showErrorFeedback(t("contextManagement.feedback.embeddingResourceRequired"), t("contextManagement.feedback.createFailed"));
      return;
    }
    if (selectedChunkingStrategy !== "fixed_length") {
      showErrorFeedback(t("contextManagement.feedback.chunkingStrategyRequired"), t("contextManagement.feedback.createFailed"));
      return;
    }
    const normalizedChunkLength = Number.parseInt(chunkLength, 10);
    if (!Number.isInteger(normalizedChunkLength) || normalizedChunkLength <= 0) {
      showErrorFeedback(t("contextManagement.feedback.chunkLengthInvalid"), t("contextManagement.feedback.createFailed"));
      return;
    }
    const normalizedChunkOverlap = Number.parseInt(chunkOverlap, 10);
    if (!Number.isInteger(normalizedChunkOverlap) || normalizedChunkOverlap < 0) {
      showErrorFeedback(t("contextManagement.feedback.chunkOverlapInvalid"), t("contextManagement.feedback.createFailed"));
      return;
    }
    if (normalizedChunkOverlap >= normalizedChunkLength) {
      showErrorFeedback(t("contextManagement.feedback.chunkOverlapTooLarge"), t("contextManagement.feedback.createFailed"));
      return;
    }
    let schema: KnowledgeBaseSchema | undefined;
    try {
      schema = parseSchemaText(schemaText);
    } catch {
      showErrorFeedback(t("contextManagement.feedback.invalidSchema"), t("contextManagement.feedback.createFailed"));
      return;
    }
    setSaving(true);
    try {
      const knowledgeBase = await createKnowledgeBase({
        slug,
        display_name: displayName,
        description,
        backing_provider_instance_id: selectedProviderId,
        lifecycle_state: "active",
        schema,
        vectorization: {
          mode: selectedVectorizationMode,
          ...(selectedVectorizationMode === "vanessa_embeddings"
            ? {
                embedding_provider_instance_id: selectedEmbeddingProviderId,
                embedding_resource_id: selectedEmbeddingResourceId,
              }
            : {}),
        },
        chunking: {
          strategy: selectedChunkingStrategy,
          config: {
            unit: "tokens",
            chunk_length: normalizedChunkLength,
            chunk_overlap: normalizedChunkOverlap,
          },
        },
      }, token);
      navigate(`/control/context/${knowledgeBase.id}`, {
        state: withActionFeedbackState({
          kind: "success",
          message: t("contextManagement.feedback.created", { name: knowledgeBase.display_name }),
        }),
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.createFailed"));
    } finally {
      setSaving(false);
    }
  }

  return {
    slug,
    displayName,
    description,
    schemaText,
    schemaTextError,
    schemaProperties,
    schemaEditorMode,
    schemaProfiles,
    providerOptions: enabledVectorProviders,
    selectedProviderId,
    selectedProviderKey,
    vectorizationOptions,
    vectorizationLoadError,
    vectorizationOptionsLoading,
    selectedVectorizationMode,
    selectedEmbeddingProviderId,
    selectedEmbeddingResourceId,
    selectedEmbeddingProviderReady,
    selectedEmbeddingProviderNeedsModel,
    selectedEmbeddingProviderUnavailableReason: selectedEmbeddingProvider?.unavailable_reason ?? null,
    selectedEmbeddingProviderDisplayName: selectedEmbeddingProvider?.display_name ?? selectedEmbeddingProvider?.id ?? "",
    selectedChunkingStrategy,
    chunkLength,
    chunkOverlap,
    selectedProfileId,
    selectedProfileDescription,
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
    setSelectedProviderId,
    setSelectedVectorizationMode,
    setSelectedEmbeddingProviderId,
    setSelectedEmbeddingResourceId,
    setSelectedChunkingStrategy,
    setChunkLength,
    setChunkOverlap,
    setSchemaEditorMode,
    setSchemaText,
    setSelectedProfileId: selectSchemaProfile,
    setSaveProfileSlug,
    setSaveProfileDisplayName,
    setSaveProfileDescription,
    toggleSaveProfileOpen,
    addSchemaProperty,
    removeSchemaProperty,
    updateSchemaProperty,
    saveCurrentSchemaProfile,
    handleSubmit,
  };
}

function buildSuggestedProfileSlug(
  selectedProfile: KnowledgeBaseSchemaProfile | null,
  displayName: string,
  slug: string,
): string {
  if (selectedProfile) {
    return `${selectedProfile.slug}-custom`;
  }
  return slugify(displayName || slug || "custom-schema");
}

function buildSuggestedProfileDisplayName(
  selectedProfile: KnowledgeBaseSchemaProfile | null,
  displayName: string,
): string {
  if (selectedProfile) {
    return `${selectedProfile.display_name} Custom`;
  }
  return displayName.trim() ? `${displayName.trim()} schema` : "Custom schema profile";
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    || "custom-schema";
}
