export type ToolTestInputObject = Record<string, unknown>;
export type ToolTestImageField = "image" | "car_image" | "logo_image";

export function stringifyToolTestInput(value: ToolTestInputObject): string {
  return JSON.stringify(value, null, 2);
}

export function parseToolTestInput(text: string): ToolTestInputObject {
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as ToolTestInputObject : {};
  } catch {
    return {};
  }
}

export function readImageFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const commaIndex = result.indexOf(",");
      resolve(commaIndex >= 0 ? result.slice(commaIndex + 1) : result);
    };
    reader.onerror = () => reject(reader.error ?? new Error("Unable to read image file."));
    reader.readAsDataURL(file);
  });
}

export async function applyImageFileToToolTestInput(
  inputText: string,
  fieldName: ToolTestImageField,
  file: File,
): Promise<string> {
  const dataBase64 = await readImageFileAsBase64(file);
  const input = parseToolTestInput(inputText);
  const nextInput = {
    ...input,
    [fieldName]: {
      data_base64: dataBase64,
      mime_type: file.type || "application/octet-stream",
    },
  };
  return stringifyToolTestInput(nextInput);
}
