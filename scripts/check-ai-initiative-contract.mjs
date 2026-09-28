#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CONTRACT_PATH = join(ROOT, "shared/contracts/mvp-surface.json");
const INVENTORY_PATH = join(ROOT, "docs/architecture/generated/ai-initiative-capability-inventory.json");

const EXPECTED_IDS = [
  "ai.initiative.read",
  "ai.initiative.write",
  "ai.initiative.transition",
  "ai.initiative.portfolio.read",
];

const raw = readFileSync(CONTRACT_PATH, "utf8");
const manifest = JSON.parse(raw);
const capsById = new Map(manifest.capabilities.map((c) => [c.id, c]));

const errors = [];

for (const id of EXPECTED_IDS) {
  const cap = capsById.get(id);
  if (!cap) {
    errors.push(`Missing required capability in contract: ${id}`);
    continue;
  }
  if (!cap.enabled) errors.push(`${id}: must be enabled`);
  if (!cap.requires_workspace) errors.push(`${id}: requires_workspace must be true`);
  if (!cap.requires_project) errors.push(`${id}: requires_project must be true`);
  if (!cap.path || !cap.path.includes(":projectId")) errors.push(`${id}: path must contain :projectId`);
  if (cap.owner !== "company-operations") errors.push(`${id}: owner must be company-operations`);
  if (cap.plane !== "company") errors.push(`${id}: plane must be company`);
  if (cap.source_kind !== "company_db") errors.push(`${id}: source_kind must be company_db`);
  if (!cap.backend_test) errors.push(`${id}: backend_test must be defined`);
  if (!cap.flutter_test) errors.push(`${id}: flutter_test must be defined`);
  if (!cap.integration_test) errors.push(`${id}: integration_test must be defined`);
}

if (!existsSync(INVENTORY_PATH)) {
  errors.push(`Inventory file not found: ${INVENTORY_PATH}`);
} else {
  const inventory = JSON.parse(readFileSync(INVENTORY_PATH, "utf8"));
  const invIds = new Set((inventory.capabilities || []).map((c) => c.id));
  for (const id of EXPECTED_IDS) {
    if (!invIds.has(id)) {
      errors.push(`Inventory file missing capability: ${id}`);
    }
  }
}

if (errors.length > 0) {
  console.error("AI Initiative Contract Check FAILED:");
  for (const err of errors) {
    console.error(` - ${err}`);
  }
  process.exit(1);
}

console.log("[OK] AI Initiative Contract Check passed.");
