/**
 * GENERATED FILE — DO NOT MODIFY DIRECTLY
 * Source: shared/contracts/startup-team-profiles.json · Generator: scripts/gen-startup-team-profiles.mjs
 * To update: edit shared/contracts/startup-team-profiles.json and run `node scripts/gen-startup-team-profiles.mjs`
 */

export type AssignmentState = 'TEMPLATE' | 'ACTIVE' | 'PAUSED' | 'RETIRED';
export type TeamDisplayState = 'CHAT_READY' | AssignmentState;

export type RuntimeReadiness =
  | 'READY'
  | 'PENDING_CRM_FOUNDATION'
  | 'PENDING_PROJECT_KNOWLEDGE'
  | 'DEFERRED_CODING';

export type StartupTeamProfileKey =
  | "founder_assistant"
  | "operations"
  | "research_intelligence"
  | "strategy"
  | "marketing"
  | "finance"
  | "crm"
  | "sales"
  | "coding"
  | "product"
  | "people"
  | "customer_support";

export const STARTUP_TEAM_PROFILE_KEYS = [
  "founder_assistant",
  "operations",
  "research_intelligence",
  "strategy",
  "marketing",
  "finance",
  "crm",
  "sales",
  "coding",
  "product",
  "people",
  "customer_support",
] as const;

export interface StartupTeamProfileDef {
  key: StartupTeamProfileKey;
  label: string;
  defaultMode: string;
  runtimeReadiness: RuntimeReadiness;
}

export const STARTUP_TEAM_PROFILES: readonly StartupTeamProfileDef[] = Object.freeze([
  {"key":"founder_assistant","label":"Co-Founder","defaultMode":"CHAT_READY","runtimeReadiness":"READY"},
  {"key":"operations","label":"Operations","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"research_intelligence","label":"Research & Intelligence","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"strategy","label":"Strategy","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"marketing","label":"Marketing","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"finance","label":"Finance","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"crm","label":"CRM","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_CRM_FOUNDATION"},
  {"key":"sales","label":"Sales","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"coding","label":"Coding","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"product","label":"Product","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"people","label":"People","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
  {"key":"customer_support","label":"Customer Support","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
]);

export interface ProjectStartupTeamMember {
  profileKey: StartupTeamProfileKey;
  label: string;
  displayState: TeamDisplayState;
  runtimeReadiness: RuntimeReadiness;
  disabledReason?: string;
  assignmentVersion?: number;
  activatedAt?: string;
  activatedBy?: string;
}

export function isStartupTeamProfileKey(val: unknown): val is StartupTeamProfileKey {
  return typeof val === 'string' && (STARTUP_TEAM_PROFILE_KEYS as readonly string[]).includes(val);
}

export const STARTUP_TEAM_PROFILES_MAP: Readonly<Record<StartupTeamProfileKey, StartupTeamProfileDef>> = Object.freeze(
  Object.fromEntries(STARTUP_TEAM_PROFILES.map((p) => [p.key, p])) as Record<StartupTeamProfileKey, StartupTeamProfileDef>
);
