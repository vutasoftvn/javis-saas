export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];

export interface JsonObject {
  [key: string]: JsonValue;
}

export function isJsonValue(value: unknown): value is JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return true;
  }

  if (typeof value === "number") {
    return Number.isFinite(value);
  }

  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }

  if (typeof value !== "object") {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return false;

  return Object.values(value).every(isJsonValue);
}

export function isJsonObject(value: unknown): value is JsonObject {
  return value !== null && !Array.isArray(value) && typeof value === "object" && isJsonValue(value);
}

export function toJsonObject(value: unknown): JsonObject {
  return isJsonObject(value) ? value : {};
}

export function toJsonArray(value: unknown): JsonValue[] {
  return Array.isArray(value) && value.every(isJsonValue) ? value : [];
}
