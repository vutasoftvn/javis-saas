import { createHash } from "node:crypto";

export function canonicalJsonStringify(obj: any): string {
  if (obj === null || typeof obj !== "object") {
    if (typeof obj === "bigint") {
      return JSON.stringify(obj.toString());
    }
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    return "[" + obj.map((item) => canonicalJsonStringify(item)).join(",") + "]";
  }

  const keys = Object.keys(obj).sort();
  const pairs = keys.map(
    (k) => JSON.stringify(k) + ":" + canonicalJsonStringify(obj[k])
  );
  return "{" + pairs.join(",") + "}";
}

export function computeCanonicalSha256(content: any): string {
  const canonicalStr = canonicalJsonStringify(content);
  const hash = createHash("sha256").update(canonicalStr).digest("hex");
  return `sha256:${hash}`;
}
