import type {
  KnowledgeBaseSchema,
  KnowledgeBaseSchemaProperty,
  KnowledgeBaseSchemaPropertyType,
} from "../../api/context";

export const SCHEMA_PROPERTY_TYPES: KnowledgeBaseSchemaPropertyType[] = ["text", "number", "int", "boolean"];

export function createDefaultSchemaProperty(index: number): KnowledgeBaseSchemaProperty {
  return {
    name: `field_${index + 1}`,
    data_type: "text",
  };
}

export function buildSchemaFromProperties(properties: KnowledgeBaseSchemaProperty[]): KnowledgeBaseSchema {
  return {
    properties: properties.map((property) => ({
      name: property.name,
      data_type: property.data_type,
    })),
  };
}

export function schemaToPrettyJson(schema: KnowledgeBaseSchema): string {
  return JSON.stringify(schema, null, 2);
}

export function parseSchemaText(text: string): KnowledgeBaseSchema {
  if (!text.trim()) {
    return {};
  }
  const parsed = JSON.parse(text) as unknown;
  return normalizeSchema(parsed);
}

export function normalizeSchema(value: unknown): KnowledgeBaseSchema {
  if (value === null || value === undefined) {
    return {};
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new Error("schema must be an object");
  }
  const schema = value as Record<string, unknown>;
  const rawProperties = schema.properties;
  if (rawProperties === undefined) {
    return {};
  }
  if (!Array.isArray(rawProperties)) {
    throw new Error("schema.properties must be an array");
  }
  return {
    properties: rawProperties.map((item, index) => normalizeSchemaProperty(item, index)),
  };
}

export function schemaPropertiesFromSchema(schema: KnowledgeBaseSchema): KnowledgeBaseSchemaProperty[] {
  return Array.isArray(schema.properties)
    ? schema.properties.map((property) => ({
        name: property.name,
        data_type: property.data_type,
      }))
    : [];
}

export function schemasEqual(left: KnowledgeBaseSchema, right: KnowledgeBaseSchema): boolean {
  try {
    return JSON.stringify(normalizeSchema(left)) === JSON.stringify(normalizeSchema(right));
  } catch {
    return false;
  }
}

function normalizeSchemaProperty(item: unknown, index: number): KnowledgeBaseSchemaProperty {
  if (typeof item !== "object" || item === null || Array.isArray(item)) {
    throw new Error(`schema.properties[${index}] must be an object`);
  }
  const property = item as Record<string, unknown>;
  const name = String(property.name ?? "").trim();
  const dataType = String(property.data_type ?? "text").trim().toLowerCase();
  if (!name) {
    throw new Error(`schema.properties[${index}].name is required`);
  }
  if (!SCHEMA_PROPERTY_TYPES.includes(dataType as KnowledgeBaseSchemaPropertyType)) {
    throw new Error(`schema.properties[${index}].data_type must be one of text, number, int, boolean`);
  }
  return {
    name,
    data_type: dataType as KnowledgeBaseSchemaPropertyType,
  };
}
