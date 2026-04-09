import { describe, expect, it } from "vitest";
import {
  buildMetadataRecord,
  createEmptyMetadataEntry,
  formatMetadataValue,
  MetadataEditorValidationError,
} from "./metadataEditor";

const schema = {
  properties: [
    { name: "category", data_type: "text" as const },
    { name: "score", data_type: "number" as const },
    { name: "page_count", data_type: "int" as const },
    { name: "published", data_type: "boolean" as const },
  ],
};

describe("metadataEditor helpers", () => {
  it("builds typed metadata records from entry rows", () => {
    const category = createEmptyMetadataEntry();
    const score = createEmptyMetadataEntry();
    const pageCount = createEmptyMetadataEntry();
    const published = createEmptyMetadataEntry();

    const payload = buildMetadataRecord(
      [
        { ...category, propertyName: "category", value: "guide" },
        { ...score, propertyName: "score", value: "0.75" },
        { ...pageCount, propertyName: "page_count", value: "12" },
        { ...published, propertyName: "published", value: "true" },
      ],
      schema,
    );

    expect(payload).toEqual({
      category: "guide",
      score: 0.75,
      page_count: 12,
      published: true,
    });
  });

  it("rejects duplicate property names", () => {
    const first = createEmptyMetadataEntry();
    const second = createEmptyMetadataEntry();

    expect(() =>
      buildMetadataRecord(
        [
          { ...first, propertyName: "category", value: "guide" },
          { ...second, propertyName: "category", value: "another" },
        ],
        schema,
      ),
    ).toThrowError(MetadataEditorValidationError);
  });

  it("formats metadata values for viewing", () => {
    expect(formatMetadataValue(true)).toBe("true");
    expect(formatMetadataValue(12)).toBe("12");
    expect(formatMetadataValue("guide")).toBe("guide");
  });
});
