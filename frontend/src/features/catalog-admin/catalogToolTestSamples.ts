import type { CatalogTool } from "../../api/catalog";

function buildSampleValueFromSchema(schema: unknown, propertyName = ""): unknown {
  if (!schema || typeof schema !== "object" || Array.isArray(schema)) {
    if (propertyName === "query") {
      return "OpenAI platform runtime";
    }
    if (propertyName === "code") {
      return "print('Hello from VANESSA')";
    }
    if (propertyName === "timeout_seconds" || propertyName === "top_k") {
      return 3;
    }
    return "";
  }

  const schemaObject = schema as Record<string, unknown>;
  const schemaType = String(schemaObject.type ?? "").trim().toLowerCase();
  const enumValues = Array.isArray(schemaObject.enum) ? schemaObject.enum : [];
  if (enumValues.length > 0) {
    return enumValues[0];
  }

  if (schemaType === "object" || schemaObject.properties) {
    const properties = schemaObject.properties && typeof schemaObject.properties === "object"
      ? schemaObject.properties as Record<string, unknown>
      : {};
    const required = Array.isArray(schemaObject.required)
      ? schemaObject.required.filter((item): item is string => typeof item === "string")
      : [];
    const propertyKeys = required.length > 0 ? required : Object.keys(properties).slice(0, 3);
    const result: Record<string, unknown> = {};
    for (const key of propertyKeys) {
      if (!(key in properties)) {
        continue;
      }
      result[key] = buildSampleValueFromSchema(properties[key], key);
    }
    return result;
  }

  if (schemaType === "array") {
    return [buildSampleValueFromSchema(schemaObject.items, propertyName)];
  }

  if (schemaType === "integer" || schemaType === "number") {
    const minimum = schemaObject.minimum;
    return typeof minimum === "number" ? minimum : 1;
  }

  if (schemaType === "boolean") {
    return false;
  }

  if (propertyName === "query") {
    return "OpenAI platform runtime";
  }
  if (propertyName === "code") {
    return "print('Hello from VANESSA')";
  }
  if (propertyName === "tool_name") {
    return "example_tool";
  }
  return "example";
}

export function buildSampleToolInput(tool: CatalogTool): Record<string, unknown> {
  if (tool.id === "tool.web_search" || tool.spec.tool_name === "web_search") {
    return {
      query: "OpenAI platform runtime",
      top_k: 3,
    };
  }

  if (tool.id === "tool.python_exec" || tool.spec.tool_name === "python_exec") {
    return {
      code: "numbers = input_payload.get('numbers', [1, 2, 3])\nresult = sum(numbers)\nprint(f'Sum: {result}')",
      input: {
        numbers: [1, 2, 3],
      },
      timeout_seconds: 5,
    };
  }

  return buildSampleValueFromSchema(tool.spec.input_schema) as Record<string, unknown>;
}
