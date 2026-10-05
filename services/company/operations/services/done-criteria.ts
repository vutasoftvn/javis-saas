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

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseCriterion(raw: unknown, seen: Set<string>): DoneCriterion {
  if (!isRecord(raw)) throw new Error("invalid criterion id");
  const id = raw.id;
  if (typeof id !== "string" || !ID_PATTERN.test(id)) throw new Error("invalid criterion id");
  if (seen.has(id)) throw new Error("duplicate criterion id");
  seen.add(id);

  const description = typeof raw.description === "string" ? raw.description.trim() : "";
  if (description.length < 1 || description.length > 300) {
    throw new Error("description must be 1..300 chars");
  }
  const required = typeof raw.required === "boolean" ? raw.required : true;

  if (raw.check === "deterministic") {
    const p = raw.predicate;
    if (!isRecord(p)) throw new Error("deterministic criterion requires predicate");
    if (!PREDICATE_KINDS.includes(p.kind as PredicateKind)) throw new Error("unknown predicate kind");
    if (!isRecord(p.args)) throw new Error("deterministic criterion requires predicate");
    return {
      id,
      description,
      required,
      check: "deterministic",
      predicate: { kind: p.kind as PredicateKind, args: p.args },
    };
  }
  if (raw.check === "rubric") {
    const rubric = typeof raw.rubric === "string" ? raw.rubric.trim() : "";
    if (rubric.length < 1 || rubric.length > 500) throw new Error("rubric criterion requires rubric");
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
