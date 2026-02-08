import crypto from "crypto";

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    const items = value.map((item) => stableStringify(item));
    return `[${items.join(",")}]`;
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  const props = keys.map((key) => `${JSON.stringify(key)}:${stableStringify(obj[key])}`);
  return `{${props.join(",")}}`;
}

export function canonicalActions(actions: Array<Record<string, unknown>>): string {
  return stableStringify(actions);
}

export function commitHash(actions: Array<Record<string, unknown>>, nonce: string): string {
  const payload = canonicalActions(actions) + nonce;
  return crypto.createHash("sha256").update(payload).digest("hex");
}
