import { APIError } from "encore.dev/api";
import { AutomationFacts, FACT_KEYS } from "./facts";

export type Op = "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "in" | "not_in" | "contains";

export const VALID_OPS: ReadonlySet<string> = new Set([
  "eq",
  "ne",
  "gt",
  "gte",
  "lt",
  "lte",
  "in",
  "not_in",
  "contains",
]);

export type Predicate =
  | { all: Predicate[] }
  | { any: Predicate[] }
  | { not: Predicate }
  | { fact: string; op: Op; value: string | number | boolean | Array<string | number> };

function resolveFactValue(factPath: string, facts: AutomationFacts): any {
  if (factPath === "labels") {
    return facts.labels;
  }
  const parts = factPath.split(".");
  let curr: any = facts;
  for (const part of parts) {
    if (curr === null || curr === undefined) return null;
    curr = curr[part];
  }
  return curr ?? null;
}

export function evaluatePredicate(node: Predicate, facts: AutomationFacts): boolean {
  if ("all" in node) {
    return node.all.every((child) => evaluatePredicate(child, facts));
  }

  if ("any" in node) {
    return node.any.some((child) => evaluatePredicate(child, facts));
  }

  if ("not" in node) {
    return !evaluatePredicate(node.not, facts);
  }

  if ("fact" in node && "op" in node) {
    const factVal = resolveFactValue(node.fact, facts);
    const targetVal = node.value;

    switch (node.op) {
      case "eq":
        return factVal === targetVal;
      case "ne":
        return factVal !== targetVal;
      case "gt":
        if (typeof factVal !== "number" || typeof targetVal !== "number") return false;
        return factVal > targetVal;
      case "gte":
        if (typeof factVal !== "number" || typeof targetVal !== "number") return false;
        return factVal >= targetVal;
      case "lt":
        if (typeof factVal !== "number" || typeof targetVal !== "number") return false;
        return factVal < targetVal;
      case "lte":
        if (typeof factVal !== "number" || typeof targetVal !== "number") return false;
        return factVal <= targetVal;
      case "in":
        if (!Array.isArray(targetVal)) return false;
        return (targetVal as any[]).includes(factVal);
      case "not_in":
        if (!Array.isArray(targetVal)) return false;
        return !(targetVal as any[]).includes(factVal);
      case "contains":
        if (!Array.isArray(factVal)) return false;
        return factVal.includes(targetVal as any);
      default:
        return false;
    }
  }

  return false;
}

export function validatePredicate(node: Predicate): void {
  if (!node || typeof node !== "object") {
    throw APIError.invalidArgument("Predicate node must be an object");
  }

  if ("all" in node) {
    if (!Array.isArray(node.all)) {
      throw APIError.invalidArgument("'all' predicate must be an array");
    }
    node.all.forEach(validatePredicate);
    return;
  }

  if ("any" in node) {
    if (!Array.isArray(node.any)) {
      throw APIError.invalidArgument("'any' predicate must be an array");
    }
    node.any.forEach(validatePredicate);
    return;
  }

  if ("not" in node) {
    validatePredicate(node.not);
    return;
  }

  if ("fact" in node && "op" in node) {
    if (!FACT_KEYS.has(node.fact)) {
      throw APIError.invalidArgument(`Invalid fact key: ${node.fact}`);
    }

    if (!VALID_OPS.has(node.op)) {
      throw APIError.invalidArgument(`Invalid operator: ${node.op}`);
    }

    if (node.op === "contains" && node.fact !== "labels") {
      throw APIError.invalidArgument(`'contains' operator is only supported on array facts (e.g. 'labels')`);
    }

    if ((node.op === "in" || node.op === "not_in") && !Array.isArray(node.value)) {
      throw APIError.invalidArgument(`'${node.op}' operator requires an array value`);
    }

    return;
  }

  throw APIError.invalidArgument("Invalid predicate structure");
}
