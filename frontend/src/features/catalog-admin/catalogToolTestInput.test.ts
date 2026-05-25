import { describe, expect, it } from "vitest";
import { parseToolTestInput, stringifyToolTestInput } from "./catalogToolTestInput";

describe("catalogToolTestInput", () => {
  it("parses object input and falls back for invalid json", () => {
    expect(parseToolTestInput('{"query":"hello"}')).toEqual({ query: "hello" });
    expect(parseToolTestInput("[]")).toEqual({});
    expect(parseToolTestInput("{oops")).toEqual({});
  });

  it("stringifies tool test input consistently", () => {
    expect(stringifyToolTestInput({ query: "hello", top_k: 3 })).toBe('{\n  "query": "hello",\n  "top_k": 3\n}');
  });
});
