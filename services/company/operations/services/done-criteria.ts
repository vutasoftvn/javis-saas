export type DoneCriterionCheck = "deterministic" | "rubric";
export type PredicateKind = "artifact_exists" | "metric_gte" | "field_present";

export interface DoneCriterion {
  id: string;
  description: string;
  required: boolean;
  check: DoneCriterionCheck;
  predicate?: { kind: PredicateKind; args: Record<string, unknown> };
  rubric?: string;
}

export interface DoneCriteria {
  version: 1;
  criteria: DoneCriterion[];
}

const ID_PATTERN = /^[a-z0-9_-]{1,40}$/;
const PREDICATE_KINDS: readonly PredicateKind[] = ["artifact_exists", "metric_gte", "field_present"];

// Whitespace set shared with packages/agent/contracts/done_criteria.py (_WS):
// JS WhiteSpace + LineTerminator. Keep both lists identical.
const WS_CHARS = new Set<string>(
  "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff".split(
    "",
  ),
);

/** Linear-time trim (a regex like ^WS+|WS+$ is quadratic on long internal runs). */
function trimWs(s: string): string {
  let start = 0;
  let end = s.length;
  while (start < end && WS_CHARS.has(s[start]!)) start++;
  while (end > start && WS_CHARS.has(s[end - 1]!)) end--;
  return s.slice(start, end);
}

// Raw strings longer than 4x the limit are rejected before trimming (same rule in Python).
const RAW_FACTOR = 4;
// Canonical size = UTF-8 bytes of JSON.stringify(args); Python mirrors it in js_canonical_json_size.
const MAX_ARGS_BYTES = 2048;

/** Length in Unicode code points (matches Python len). */
function cpLen(s: string): number {
  return Array.from(s).length;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseCriterion(raw: unknown, seen: Set<string>): DoneCriterion {
  if (!isRecord(raw)) throw new Error("invalid criterion id");
  const id = raw.id;
  if (typeof id !== "string" || !ID_PATTERN.test(id)) throw new Error("invalid criterion id");
  if (seen.has(id)) throw new Error("duplicate criterion id");
  seen.add(id);

  const rawDescription = typeof raw.description === "string" ? raw.description : "";
  if (cpLen(rawDescription) > 300 * RAW_FACTOR) throw new Error("description must be 1..300 chars");
  const description = trimWs(rawDescription);
  if (cpLen(description) < 1 || cpLen(description) > 300) {
    throw new Error("description must be 1..300 chars");
  }
  const required = typeof raw.required === "boolean" ? raw.required : true;

  if (raw.check === "deterministic") {
    const p = raw.predicate;
    if (!isRecord(p)) throw new Error("deterministic criterion requires predicate");
    if (!PREDICATE_KINDS.includes(p.kind as PredicateKind)) throw new Error("unknown predicate kind");
    if (!isRecord(p.args)) throw new Error("deterministic criterion requires predicate");
    if (new TextEncoder().encode(JSON.stringify(p.args)).length > MAX_ARGS_BYTES) {
      throw new Error("predicate args too large");
    }
    return {
      id,
      description,
      required,
      check: "deterministic",
      predicate: { kind: p.kind as PredicateKind, args: p.args },
    };
  }
  if (raw.check === "rubric") {
    const rawRubric = typeof raw.rubric === "string" ? raw.rubric : "";
    if (cpLen(rawRubric) > 500 * RAW_FACTOR) throw new Error("rubric criterion requires rubric");
    const rubric = trimWs(rawRubric);
    if (cpLen(rubric) < 1 || cpLen(rubric) > 500) throw new Error("rubric criterion requires rubric");
    return { id, description, required, check: "rubric", rubric };
  }
  throw new Error("invalid check");
}

export function parseDoneCriteria(raw: unknown): DoneCriteria {
  if (!isRecord(raw) || raw.version !== 1) throw new Error("unsupported version");
  const list = raw.criteria;
  if (!Array.isArray(list) || list.length < 1 || list.length > 10) {
    throw new Error("criteria must contain 1..10 items");
  }
  const seen = new Set<string>();
  return { version: 1, criteria: list.map((c) => parseCriterion(c, seen)) };
}
