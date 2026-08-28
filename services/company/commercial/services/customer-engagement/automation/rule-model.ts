import { APIError } from "encore.dev/api";
import { Predicate, validatePredicate } from "./predicate";
import { AutomationAction, validateAction } from "./actions";

export interface AutomationRule {
  id?: string;
  workspaceId?: string;
  ruleKey: string;
  version: number;
  name: string;
  trigger: "thread_opened" | "message_received" | "thread_status_changed" | "csat_recorded" | "time_sweep";
  priority: number;
  condition: Predicate;
  actions: AutomationAction[];
  enabled: boolean;
  stopOnMatch: boolean;
  effectiveFrom?: Date;
  effectiveUntil?: Date | null;
  createdByWorkforceMemberId?: string | null;
  createdAt?: Date;
}

export const VALID_TRIGGERS: ReadonlySet<string> = new Set([
  "thread_opened",
  "message_received",
  "thread_status_changed",
  "csat_recorded",
  "time_sweep",
]);

export function validateRule(rule: AutomationRule): void {
  if (!rule.ruleKey || typeof rule.ruleKey !== "string") {
    throw APIError.invalidArgument("ruleKey is required and must be a string");
  }

  if (!rule.name || typeof rule.name !== "string") {
    throw APIError.invalidArgument("name is required and must be a string");
  }

  if (!VALID_TRIGGERS.has(rule.trigger)) {
    throw APIError.invalidArgument(`Invalid trigger: ${rule.trigger}`);
  }

  validatePredicate(rule.condition);

  if (!Array.isArray(rule.actions) || rule.actions.length === 0) {
    throw APIError.invalidArgument("actions must be a non-empty array");
  }

  for (const action of rule.actions) {
    validateAction(action);
  }
}
