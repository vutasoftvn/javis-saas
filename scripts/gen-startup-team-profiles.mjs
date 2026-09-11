#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "shared/contracts/startup-team-profiles.json");
const TS_OUT = join(ROOT, "services/company/shared/contracts/startup-team-profiles.generated.ts");
const PY_OUT = join(ROOT, "apps/cosa/agents/startup_team_profiles_generated.py");

const CHECK = process.argv.includes("--check");

const raw = readFileSync(SRC, "utf8");
const spec = JSON.parse(raw);

if (!spec.profiles || !Array.isArray(spec.profiles)) {
  console.error("Error: startup-team-profiles.json must contain a 'profiles' array");
  process.exit(1);
}

const seenKeys = new Set();
for (const p of spec.profiles) {
  if (!p.key || typeof p.key !== "string") {
    console.error("Invalid profile: missing key", p);
    process.exit(1);
  }
  if (seenKeys.has(p.key)) {
    console.error(`Duplicate profile key: ${p.key}`);
    process.exit(1);
  }
  seenKeys.add(p.key);
  if (!p.runtimeReadiness || typeof p.runtimeReadiness !== "string") {
    console.error(`Profile ${p.key} missing runtimeReadiness`);
    process.exit(1);
  }
}

const HEADER_LINES = [
  "GENERATED FILE — DO NOT MODIFY DIRECTLY",
  "Source: shared/contracts/startup-team-profiles.json · Generator: scripts/gen-startup-team-profiles.mjs",
  "To update: edit shared/contracts/startup-team-profiles.json and run `node scripts/gen-startup-team-profiles.mjs`",
];

function genTs() {
  const lines = [
    `/**`,
    ...HEADER_LINES.map((h) => ` * ${h}`),
    ` */`,
    "",
    `export type AssignmentState = 'TEMPLATE' | 'ACTIVE' | 'PAUSED' | 'RETIRED';`,
    `export type TeamDisplayState = 'CHAT_READY' | AssignmentState;`,
    "",
    `export type RuntimeReadiness =`,
    `  | 'READY'`,
    `  | 'PENDING_CRM_FOUNDATION'`,
    `  | 'PENDING_PROJECT_KNOWLEDGE'`,
    `  | 'DEFERRED_CODING';`,
    "",
    `export const STARTUP_TEAM_PROFILE_KEYS = [`,
    ...spec.profiles.map((p) => `  ${JSON.stringify(p.key)},`),
    `] as const;`,
    "",
    `export type StartupTeamProfileKey = (typeof STARTUP_TEAM_PROFILE_KEYS)[number];`,
    "",
    `export interface StartupTeamProfileDef {`,
    `  key: StartupTeamProfileKey;`,
    `  label: string;`,
    `  defaultMode: string;`,
    `  runtimeReadiness: RuntimeReadiness;`,
    `}`,
    "",
    `export const STARTUP_TEAM_PROFILES: readonly StartupTeamProfileDef[] = Object.freeze([`,
    ...spec.profiles.map((p) => `  ${JSON.stringify(p)},`),
    `]);`,
    "",
    `export interface ProjectStartupTeamMember {`,
    `  profileKey: StartupTeamProfileKey;`,
    `  label: string;`,
    `  displayState: TeamDisplayState;`,
    `  runtimeReadiness: RuntimeReadiness;`,
    `  disabledReason?: string;`,
    `  assignmentVersion?: number;`,
    `  activatedAt?: string;`,
    `  activatedBy?: string;`,
    `}`,
    "",
    `export function isStartupTeamProfileKey(val: unknown): val is StartupTeamProfileKey {`,
    `  return typeof val === 'string' && (STARTUP_TEAM_PROFILE_KEYS as readonly string[]).includes(val);`,
    `}`,
    "",
    `export const STARTUP_TEAM_PROFILES_MAP: Readonly<Record<StartupTeamProfileKey, StartupTeamProfileDef>> = Object.freeze(`,
    `  Object.fromEntries(STARTUP_TEAM_PROFILES.map((p) => [p.key, p])) as Record<StartupTeamProfileKey, StartupTeamProfileDef>`,
    `);`,
    "",
  ];
  return lines.join("\n");
}

function genPy() {
  const lines = [
    `# ${HEADER_LINES.join("\n# ")}`,
    "from __future__ import annotations",
    "",
    "from typing import Final, Literal",
    "",
    "StartupTeamProfileKey = Literal[",
    ...spec.profiles.map((p) => `    ${JSON.stringify(p.key)},`),
    "]",
    "",
    "RuntimeReadiness = Literal[",
    "    'READY',",
    "    'PENDING_CRM_FOUNDATION',",
    "    'PENDING_PROJECT_KNOWLEDGE',",
    "    'DEFERRED_CODING',",
    "]",
    "",
    "STARTUP_TEAM_PROFILE_KEYS: Final[tuple[StartupTeamProfileKey, ...]] = (",
    ...spec.profiles.map((p) => `    ${JSON.stringify(p.key)},`),
    ")",
    "",
    "STARTUP_TEAM_PROFILES: Final[list[dict[str, str]]] = [",
    ...spec.profiles.map((p) => `    ${JSON.stringify(p)},`),
    "]",
    "",
    "STARTUP_TEAM_PROFILES_MAP: Final[dict[str, dict[str, str]]] = {",
    ...spec.profiles.map((p) => `    ${JSON.stringify(p.key)}: ${JSON.stringify(p)},`),
    "}",
    "",
  ];
  return lines.join("\n");
}

const tsContent = genTs();
const pyContent = genPy();

if (CHECK) {
  let hasError = false;
  if (!existsSync(TS_OUT) || readFileSync(TS_OUT, "utf8") !== tsContent) {
    console.error(`Error: ${TS_OUT} is stale or missing. Run node scripts/gen-startup-team-profiles.mjs`);
    hasError = true;
  }
  if (!existsSync(PY_OUT) || readFileSync(PY_OUT, "utf8") !== pyContent) {
    console.error(`Error: ${PY_OUT} is stale or missing. Run node scripts/gen-startup-team-profiles.mjs`);
    hasError = true;
  }
  if (hasError) process.exit(1);
  console.log("Startup team profiles generated files are up to date.");
  process.exit(0);
}

writeFileSync(TS_OUT, tsContent, "utf8");
console.log(`Generated: ${TS_OUT}`);
writeFileSync(PY_OUT, pyContent, "utf8");
console.log(`Generated: ${PY_OUT}`);
