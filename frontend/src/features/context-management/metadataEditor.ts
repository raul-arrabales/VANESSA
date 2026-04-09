import type {
  KnowledgeBaseSchema,
  KnowledgeBaseSchemaProperty,
  KnowledgeBaseSchemaPropertyType,
} from "../../api/context";
import { schemaPropertiesFromSchema } from "./schemaEditor";
import type { MetadataEntryFormState } from "./types";

let metadataEntryCounter = 0;

export class MetadataEditorValidationError extends Error {
  code: "duplicate_property" | "missing_property_name" | "invalid_text" | "invalid_number" | "invalid_int" | "invalid_boolean";

  constructor(code: MetadataEditorValidationError["code"]) {
    super(code);
    this.code = code;
  }
}

export function createEmptyMetadataEntry(): MetadataEntryFormState {
  metadataEntryCounter += 1;
  return {
    id: `metadata-entry-${metadataEntryCounter}`,
    propertyName: "",
    value: "",
  };
}

export function metadataEntriesFromRecord(
  metadata: Record<string, unknown> | null | undefined,
  schema: KnowledgeBaseSchema,
): MetadataEntryFormState[] {
  const propertiesByName = buildSchemaPropertiesByName(schemaPropertiesFromSchema(schema));
  return Object.entries(metadata ?? {})
    .filter(([propertyName]) => propertiesByName.has(propertyName))
    .map(([propertyName, value]) => ({
      id: createEmptyMetadataEntry().id,
      propertyName,
      value: metadataValueToInputValue(value, propertiesByName.get(propertyName)?.data_type ?? "text"),
    }));
}

export function buildMetadataRecord(
  entries: MetadataEntryFormState[],
  schema: KnowledgeBaseSchema,
): Record<string, unknown> {
  const propertiesByName = buildSchemaPropertiesByName(schemaPropertiesFromSchema(schema));
  const normalized: Record<string, unknown> = {};
  const seen = new Set<string>();

  for (const entry of entries) {
    const propertyName = entry.propertyName.trim();
    const rawValue = entry.value.trim();
    if (!propertyName && !rawValue) {
      continue;
    }
    if (!propertyName) {
      throw new MetadataEditorValidationError("missing_property_name");
    }
    if (seen.has(propertyName)) {
      throw new MetadataEditorValidationError("duplicate_property");
    }
    const property = propertiesByName.get(propertyName);
    if (!property) {
      throw new MetadataEditorValidationError("missing_property_name");
    }
    seen.add(propertyName);
    normalized[propertyName] = coerceMetadataValue(rawValue, property.data_type);
  }

  return normalized;
}

export function getMetadataPropertyType(
  propertyName: string,
  schemaProperties: KnowledgeBaseSchemaProperty[],
): KnowledgeBaseSchemaPropertyType {
  return buildSchemaPropertiesByName(schemaProperties).get(propertyName)?.data_type ?? "text";
}

export function formatMetadataValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(value);
  }
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return JSON.stringify(value);
}

function buildSchemaPropertiesByName(
  properties: KnowledgeBaseSchemaProperty[],
): Map<string, KnowledgeBaseSchemaProperty> {
  return new Map(properties.map((property) => [property.name, property]));
}

function metadataValueToInputValue(
  value: unknown,
  propertyType: KnowledgeBaseSchemaPropertyType,
): string {
  if (propertyType === "boolean") {
    return value === true ? "true" : value === false ? "false" : "";
  }
  return formatMetadataValue(value);
}

function coerceMetadataValue(
  value: string,
  propertyType: KnowledgeBaseSchemaPropertyType,
): string | number | boolean {
  if (propertyType === "text") {
    return value;
  }
  if (propertyType === "number") {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      throw new MetadataEditorValidationError("invalid_number");
    }
    return parsed;
  }
  if (propertyType === "int") {
    if (!/^-?\d+$/.test(value)) {
      throw new MetadataEditorValidationError("invalid_int");
    }
    return Number.parseInt(value, 10);
  }
  if (propertyType === "boolean") {
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
    throw new MetadataEditorValidationError("invalid_boolean");
  }
  throw new MetadataEditorValidationError("invalid_text");
}
