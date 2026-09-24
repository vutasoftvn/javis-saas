#!/usr/bin/env node
// Sinh TS (Company + COSA control plane) và Python từ shared/contracts/executive-advisor-overlays.json.
// Hash overlay do scripts/sync_executive_advisor_overlays.py ghi từ AgentSpec đã seed.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "shared/contracts/executive-advisor-overlays.json");
const ROLES_SRC = join(ROOT, "shared/contracts/executive-advisor-roles.json");
const TS_OUTS = [
  join(ROOT, "services/company/shared/contracts/executive-advisor-overlays.generated.ts"),
  join(ROOT, "services/cosa/shared/contracts/executive-advisor-overlays.generated.ts"),
];
const PY_OUT = join(ROOT, "apps/cosa/agents/executive_advisor_overlays_generated.py");
const CHECK = process.argv.includes("--check");

const spec = JSON.parse(readFileSync(SRC, "utf8"));
const roles = JSON.parse(readFileSync(ROLES_SRC, "utf8")).roles;
const HEX = /^[0-9a-f]{64}$/;

function fail(msg) {
  console.error(`Error: ${msg}`);
  process.exit(1);
}

if (!Array.isArray(spec.overlays)) fail("executive-advisor-overlays.json must contain 'overlays'");
const seen = new Set();
for (const o of spec.overlays) {
  if (seen.has(o.roleKey)) fail(`Duplicate overlay role key: ${o.roleKey}`);
  seen.add(o.roleKey);
  const role = roles.find((r) => r.key === o.roleKey);
  if (!role) fail(`Overlay ${o.roleKey} has no role in executive-advisor-roles.json`);
  if (o.overlaySpecId !== role.requiredAgentSpec) fail(`Overlay ${o.roleKey} spec id != role requiredAgentSpec`);
  if (o.requiredProfileKey !== role.requiredProfileKey) fail(`Overlay ${o.roleKey} profile != role profile`);
  if (o.advisoryOnly !== true) fail(`Overlay ${o.roleKey} must be advisoryOnly`);
  if (!HEX.test(o.overlayDefinitionHash)) fail(`Overlay ${o.roleKey} hash invalid`);
  if (!o.skillPins || o.skillPins.length === 0) fail(`Overlay ${o.roleKey} needs skillPins`);
  for (const p of o.skillPins) if (!HEX.test(p.definitionHash)) fail(`Overlay ${o.roleKey} skill hash invalid`);
}
for (const r of roles) if (!seen.has(r.key)) fail(`Role ${r.key} has no overlay`);

const HEADER = [
  "GENERATED FILE — DO NOT MODIFY DIRECTLY",
  "Source: shared/contracts/executive-advisor-overlays.json · Generator: scripts/gen-executive-advisor-overlays.mjs",
  "To update: run scripts/sync_executive_advisor_overlays.py then node scripts/gen-executive-advisor-overlays.mjs",
];

function genTs() {
  return [
    "/**",
    ...HEADER.map((h) => ` * ${h}`),
    " */",
    "",
    "export interface PinnedSkillIdentity {",
    "  skillId: string;",
    "  version: string;",
    "  definitionHash: string;",
    "}",
    "",
    "export interface AdvisorOverlayDefinition {",
    "  roleKey: string;",
    "  overlaySpecId: string;",
    "  overlaySpecVersion: string;",
    "  overlayDefinitionHash: string;",
    "  requiredProfileKey: string;",
    "  skillPins: readonly PinnedSkillIdentity[];",
    "  advisoryOnly: true;",
    "}",
    "",
    "export const ADVISOR_OVERLAY_CATALOG: Readonly<Record<string, AdvisorOverlayDefinition>> = Object.freeze({",
    ...spec.overlays.map((o) => `  ${JSON.stringify(o.roleKey)}: Object.freeze(${JSON.stringify(o)} as AdvisorOverlayDefinition),`),
    "});",
    "",
  ].join("\n");
}

function genPy() {
  const lines = [
    `# ${HEADER.join("\n# ")}`,
    "from __future__ import annotations",
    "",
    "from dataclasses import dataclass",
    "from typing import Final",
    "",
    "",
    "@dataclass(frozen=True)",
    "class PinnedSkillIdentity:",
    "    skill_id: str",
    "    version: str",
    "    definition_hash: str",
    "",
    "",
    "@dataclass(frozen=True)",
    "class AdvisorOverlayDefinition:",
    "    role_key: str",
    "    overlay_spec_id: str",
    "    overlay_spec_version: str",
    "    overlay_definition_hash: str",
    "    required_profile_key: str",
    "    skill_pins: tuple[PinnedSkillIdentity, ...]",
    "    advisory_only: bool",
    "",
    "",
    "ADVISOR_OVERLAY_CATALOG: Final[dict[str, AdvisorOverlayDefinition]] = {",
  ];
  for (const o of spec.overlays) {
    lines.push(
      `    ${JSON.stringify(o.roleKey)}: AdvisorOverlayDefinition(`,
      `        role_key=${JSON.stringify(o.roleKey)},`,
      `        overlay_spec_id=${JSON.stringify(o.overlaySpecId)},`,
      `        overlay_spec_version=${JSON.stringify(o.overlaySpecVersion)},`,
      `        overlay_definition_hash=(`,
      `            ${JSON.stringify(o.overlayDefinitionHash)}`,
      `        ),`,
      `        required_profile_key=${JSON.stringify(o.requiredProfileKey)},`,
      `        skill_pins=(`,
    );
    for (const p of o.skillPins) {
      lines.push(
        `            PinnedSkillIdentity(`,
        `                skill_id=${JSON.stringify(p.skillId)},`,
        `                version=${JSON.stringify(p.version)},`,
        `                definition_hash=(`,
        `                    ${JSON.stringify(p.definitionHash)}`,
        `                ),`,
        `            ),`,
      );
    }
    lines.push(`        ),`, `        advisory_only=True,`, `    ),`);
  }
  lines.push("}", "");
  return lines.join("\n");
}

const outputs = [...TS_OUTS.map((f) => [f, genTs()]), [PY_OUT, genPy()]];
if (CHECK) {
  let ok = true;
  for (const [f, c] of outputs) {
    if (!existsSync(f) || readFileSync(f, "utf8") !== c) {
      console.error(`Check failed: ${f} outdated. Run node scripts/gen-executive-advisor-overlays.mjs`);
      ok = false;
    }
  }
  process.exit(ok ? 0 : 1);
}
for (const [f, c] of outputs) writeFileSync(f, c, "utf8");
console.log(`Generated:\n${outputs.map(([f]) => "  " + f).join("\n")}`);
