#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "shared/contracts/executive-advisor-roles.json");
const STARTUP_SRC = join(ROOT, "shared/contracts/startup-team-profiles.json");
const TS_OUT = join(ROOT, "services/company/shared/contracts/executive-advisor-roles.generated.ts");
const PY_OUT = join(ROOT, "apps/cosa/agents/executive_advisor_roles_generated.py");

const CHECK = process.argv.includes("--check");

const raw = readFileSync(SRC, "utf8");
const spec = JSON.parse(raw);

const startupRaw = readFileSync(STARTUP_SRC, "utf8");
const startupSpec = JSON.parse(startupRaw);
const startupProfileKeys = new Set(startupSpec.profiles.map((p) => p.key));

if (!spec.presets || !Array.isArray(spec.presets)) {
  console.error("Error: executive-advisor-roles.json must contain a 'presets' array");
  process.exit(1);
}

if (!spec.roles || !Array.isArray(spec.roles)) {
  console.error("Error: executive-advisor-roles.json must contain a 'roles' array");
  process.exit(1);
}

const seenRoleKeys = new Set();
for (const r of spec.roles) {
  if (!r.key || typeof r.key !== "string") {
    console.error("Invalid role: missing key", r);
    process.exit(1);
  }
  if (seenRoleKeys.has(r.key)) {
    console.error(`Duplicate role key: ${r.key}`);
    process.exit(1);
  }
  seenRoleKeys.add(r.key);

  if (!r.requiredSkillPins || !Array.isArray(r.requiredSkillPins) || r.requiredSkillPins.length === 0) {
    console.error(`Role ${r.key} must have non-empty requiredSkillPins`);
    process.exit(1);
  }

  if (r.runtimeReadiness === "READY") {
    const requiredProfile = startupSpec.profiles.find((p) => p.key === r.requiredProfileKey);
    if (!requiredProfile) {
      console.error(
        `Role ${r.key} is marked READY but requiredProfileKey '${r.requiredProfileKey}' does not exist in startup-team-profiles.json`
      );
      process.exit(1);
    }
    if (requiredProfile.runtimeReadiness !== "READY") {
      console.error(
        `Role ${r.key} is marked READY but requiredProfileKey '${r.requiredProfileKey}' has readiness '${requiredProfile.runtimeReadiness}', expected 'READY'`
      );
      process.exit(1);
    }
  }

  if (["chief_of_staff", "coo"].includes(r.key)) {
    if (r.requiredProfileKey !== "operations") {
      console.error(`${r.key} must require 'operations' profile`);
      process.exit(1);
    }
    const expectedOperationsReadiness = startupProfileKeys.has("operations")
      ? "READY"
      : "PENDING_OPERATIONS_PROFILE";
    if (r.runtimeReadiness !== expectedOperationsReadiness) {
      console.error(`${r.key} must have runtimeReadiness ${expectedOperationsReadiness}`);
      process.exit(1);
    }
  }
}

const seenPresetKeys = new Set();
for (const p of spec.presets) {
  if (!p.key || typeof p.key !== "string") {
    console.error("Invalid preset: missing key", p);
    process.exit(1);
  }
  if (seenPresetKeys.has(p.key)) {
    console.error(`Duplicate preset key: ${p.key}`);
    process.exit(1);
  }
  seenPresetKeys.add(p.key);

  for (const rk of p.defaultRoleKeys) {
    if (!seenRoleKeys.has(rk)) {
      console.error(`Preset ${p.key} references unknown role key: ${rk}`);
      process.exit(1);
    }
  }
}

const HEADER_LINES = [
  "GENERATED FILE — DO NOT MODIFY DIRECTLY",
  "Source: shared/contracts/executive-advisor-roles.json · Generator: scripts/gen-executive-advisor-roles.mjs",
  "To update: edit shared/contracts/executive-advisor-roles.json and run `node scripts/gen-executive-advisor-roles.mjs`",
];

function genTs() {
  const lines = [
    `/**`,
    ...HEADER_LINES.map((h) => ` * ${h}`),
    ` */`,
    "",
    `export type StartupCorePresetKey = 'startup-discovery' | 'startup-build-launch';`,
    "",
    `export type ExecutiveRoleKey =`,
    ...spec.roles.map((r, idx) => `  | ${JSON.stringify(r.key)}${idx === spec.roles.length - 1 ? ";" : ""}`),
    "",
    `export type ExecutiveRuntimeReadiness =`,
    `  | 'READY'`,
    `  | 'PENDING_OPERATIONS_PROFILE'`,
    `  | 'PENDING_SALES_PROFILE'`,
    `  | 'PENDING_PRODUCT_PROFILE'`,
    `  | 'PENDING_CUSTOMER_SUPPORT_PROFILE'`,
    `  | 'PENDING_PEOPLE_PROFILE'`,
    `  | 'PENDING_SECURITY_PROFILE'`,
    `  | 'PENDING_LEGAL_PROFILE'`,
    `  | 'PENDING_DATA_PROFILE'`,
    `  | 'PENDING_AI_GOVERNANCE_PROFILE'`,
    `  | 'PENDING_ENGINEERING_PROFILE';`,
    "",
    `export const EXECUTIVE_ROLE_KEYS = [`,
    ...spec.roles.map((r) => `  ${JSON.stringify(r.key)},`),
    `] as const;`,
    "",
    `export const STARTUP_CORE_PRESET_KEYS = [`,
    ...spec.presets.map((p) => `  ${JSON.stringify(p.key)},`),
    `] as const;`,
    "",
    `export interface ExecutiveAdvisorRoleDef {`,
    `  key: ExecutiveRoleKey;`,
    `  label: string;`,
    `  advisoryRemit: string;`,
    `  requiredProfileKey: string;`,
    `  requiredAgentSpec: string;`,
    `  requiredSkillPins: readonly string[];`,
    `  advisoryOnly: boolean;`,
    `  runtimeReadiness: ExecutiveRuntimeReadiness;`,
    `  sourceProvenance: string;`,
    `}`,
    "",
    `export interface StartupCorePresetDef {`,
    `  key: StartupCorePresetKey;`,
    `  label: string;`,
    `  description: string;`,
    `  defaultRoleKeys: readonly ExecutiveRoleKey[];`,
    `}`,
    "",
    `export const EXECUTIVE_ROLE_CATALOG: Readonly<Record<ExecutiveRoleKey, ExecutiveAdvisorRoleDef>> = Object.freeze({`,
    ...spec.roles.map((r) => `  ${JSON.stringify(r.key)}: Object.freeze(${JSON.stringify(r)} as unknown as ExecutiveAdvisorRoleDef),`),
    `});`,
    "",
    `export const STARTUP_CORE_PRESETS: Readonly<Record<StartupCorePresetKey, StartupCorePresetDef>> = Object.freeze({`,
    ...spec.presets.map((p) => `  ${JSON.stringify(p.key)}: Object.freeze(${JSON.stringify(p)} as unknown as StartupCorePresetDef),`),
    `});`,
    "",
    `export function isExecutiveRoleKey(val: unknown): val is ExecutiveRoleKey {`,
    `  return typeof val === 'string' && (EXECUTIVE_ROLE_KEYS as readonly string[]).includes(val);`,
    `}`,
    "",
    `export function isStartupCorePresetKey(val: unknown): val is StartupCorePresetKey {`,
    `  return typeof val === 'string' && (STARTUP_CORE_PRESET_KEYS as readonly string[]).includes(val);`,
    `}`,
    "",
  ];
  return lines.join("\n");
}

function genPy() {
  const lines = [
    `# ${HEADER_LINES.join("\n# ")}`,
    "from __future__ import annotations",
    "",
    "from dataclasses import dataclass",
    "from typing import Final, Literal",
    "",
    "StartupCorePresetKey = Literal[",
    "    'startup-discovery',",
    "    'startup-build-launch',",
    "]",
    "",
    "ExecutiveRoleKey = Literal[",
    ...spec.roles.map((r) => `    ${JSON.stringify(r.key)},`),
    "]",
    "",
    "ExecutiveRuntimeReadiness = Literal[",
    "    'READY',",
    "    'PENDING_OPERATIONS_PROFILE',",
    "    'PENDING_SALES_PROFILE',",
    "    'PENDING_PRODUCT_PROFILE',",
    "    'PENDING_CUSTOMER_SUPPORT_PROFILE',",
    "    'PENDING_PEOPLE_PROFILE',",
    "    'PENDING_SECURITY_PROFILE',",
    "    'PENDING_LEGAL_PROFILE',",
    "    'PENDING_DATA_PROFILE',",
    "    'PENDING_AI_GOVERNANCE_PROFILE',",
    "    'PENDING_ENGINEERING_PROFILE',",
    "]",
    "",
    "EXECUTIVE_ROLE_KEYS: Final[tuple[ExecutiveRoleKey, ...]] = (",
    ...spec.roles.map((r) => `    ${JSON.stringify(r.key)},`),
    ")",
    "",
    "STARTUP_CORE_PRESET_KEYS: Final[tuple[StartupCorePresetKey, ...]] = (",
    ...spec.presets.map((p) => `    ${JSON.stringify(p.key)},`),
    ")",
    "",
    "@dataclass(frozen=True)",
    "class ExecutiveAdvisorRoleDef:",
    "    key: ExecutiveRoleKey",
    "    label: str",
    "    advisory_remit: str",
    "    required_profile_key: str",
    "    required_agent_spec: str",
    "    required_skill_pins: tuple[str, ...]",
    "    advisory_only: bool",
    "    runtime_readiness: ExecutiveRuntimeReadiness",
    "    source_provenance: str",
    "",
    "@dataclass(frozen=True)",
    "class StartupCorePresetDef:",
    "    key: StartupCorePresetKey",
    "    label: str",
    "    description: str",
    "    default_role_keys: tuple[ExecutiveRoleKey, ...]",
    "",
    "EXECUTIVE_ROLE_CATALOG: Final[dict[ExecutiveRoleKey, ExecutiveAdvisorRoleDef]] = {",
    ...spec.roles.map(
      (r) =>
        `    ${JSON.stringify(r.key)}: ExecutiveAdvisorRoleDef(`
        + `key=${JSON.stringify(r.key)}, `
        + `label=${JSON.stringify(r.label)}, `
        + `advisory_remit=${JSON.stringify(r.advisoryRemit)}, `
        + `required_profile_key=${JSON.stringify(r.requiredProfileKey)}, `
        + `required_agent_spec=${JSON.stringify(r.requiredAgentSpec)}, `
        + `required_skill_pins=(${r.requiredSkillPins.map((s) => JSON.stringify(s)).join(", ")},), `
        + `advisory_only=${r.advisoryOnly ? "True" : "False"}, `
        + `runtime_readiness=${JSON.stringify(r.runtimeReadiness)}, `
        + `source_provenance=${JSON.stringify(r.sourceProvenance)}),`
    ),
    "}",
    "",
    "STARTUP_CORE_PRESETS: Final[dict[StartupCorePresetKey, StartupCorePresetDef]] = {",
    ...spec.presets.map(
      (p) =>
        `    ${JSON.stringify(p.key)}: StartupCorePresetDef(`
        + `key=${JSON.stringify(p.key)}, `
        + `label=${JSON.stringify(p.label)}, `
        + `description=${JSON.stringify(p.description)}, `
        + `default_role_keys=(${p.defaultRoleKeys.map((k) => JSON.stringify(k)).join(", ")},)),`
    ),
    "}",
    "",
    "def is_executive_role_key(val: object) -> bool:",
    "    return isinstance(val, str) and val in EXECUTIVE_ROLE_KEYS",
    "",
    "def is_startup_core_preset_key(val: object) -> bool:",
    "    return isinstance(val, str) and val in STARTUP_CORE_PRESET_KEYS",
    "",
  ];
  return lines.join("\n");
}

const tsContent = genTs();
const pyContent = genPy();

if (CHECK) {
  let ok = true;
  if (!existsSync(TS_OUT) || readFileSync(TS_OUT, "utf8") !== tsContent) {
    console.error(`Check failed: ${TS_OUT} is outdated or missing. Run node scripts/gen-executive-advisor-roles.mjs`);
    ok = false;
  }
  if (!existsSync(PY_OUT) || readFileSync(PY_OUT, "utf8") !== pyContent) {
    console.error(`Check failed: ${PY_OUT} is outdated or missing. Run node scripts/gen-executive-advisor-roles.mjs`);
    ok = false;
  }
  process.exit(ok ? 0 : 1);
}

writeFileSync(TS_OUT, tsContent, "utf8");
writeFileSync(PY_OUT, pyContent, "utf8");
console.log(`Generated:\n  ${TS_OUT}\n  ${PY_OUT}`);
