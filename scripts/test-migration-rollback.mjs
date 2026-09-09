#!/usr/bin/env node
/**
 * Migration Gate E — Automated Migration Rollback Roundtrip Test Runner
 *
 * Tests the roundtrip resilience of database migrations across all services:
 * 1. Forward migrate all (UP)
 * 2. Reverse migrate N steps on each service using .down.sql (DOWN)
 * 3. Re-apply forward migrations (UP)
 * 4. Verify resulting schema fingerprint against deploy/schema/fingerprints.json (Gate D validation)
 *
 * Usage:
 *   node scripts/test-migration-rollback.mjs [--steps 5]
 */

import { execSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");

const DEFAULT_STEPS = 5;

function parseSteps() {
  const stepsIndex = process.argv.indexOf("--steps");
  if (stepsIndex !== -1 && process.argv[stepsIndex + 1]) {
    const s = parseInt(process.argv[stepsIndex + 1], 10);
    return isNaN(s) ? DEFAULT_STEPS : s;
  }
  return DEFAULT_STEPS;
}

function run(cmd, cwd = REPO_ROOT) {
  console.log(`> [${cwd.replace(REPO_ROOT, ".") || "."}] ${cmd}`);
  execSync(cmd, {
    cwd,
    stdio: "inherit",
    env: process.env
  });
}

function onlyBaselineMigrationsRemain() {
  // Founder Trial R1 (Task 10) — the 001 baselines have no down migration and
  // cannot be rolled back. Gate E is meaningful only once an incremental
  // migration (numbered after 001) with paired up/down SQL exists.
  const dirs = [
    join(REPO_ROOT, "packages", "agent", "migrations"),
    join(REPO_ROOT, "services", "cosa", "migrations"),
    join(REPO_ROOT, "services", "company", "identity", "migrations"),
    join(REPO_ROOT, "services", "company", "operations", "migrations"),
    join(REPO_ROOT, "services", "company", "commercial", "migrations"),
    join(REPO_ROOT, "services", "company", "finance-legal", "migrations"),
  ];
  for (const d of dirs) {
    for (const f of readdirSync(d)) {
      if ((f.endsWith(".up.sql") || (f.endsWith(".sql") && !f.endsWith(".down.sql"))) &&
          !f.startsWith("001_founder_trial_mvp_baseline")) {
        return false;
      }
    }
  }
  return true;
}

async function main() {
  const steps = parseSteps();
  console.log("================================================================================");
  console.log(`🔄 Starting Migration Gate E Roundtrip Test (Rollback Steps: ${steps})`);
  console.log("================================================================================\n");

  if (onlyBaselineMigrationsRemain()) {
    console.log(
      "⏭  Only the 001 Founder Trial baselines are present — they have no down\n" +
        "   migration by design. Gate E has nothing to roll back; skipping.\n"
    );
    return;
  }

  const pythonCmd = process.env.PYTHON || ".venv/bin/python3";

  // Phase 1: Forward Migrate All (Up)
  console.log("▶ Phase 1: Applying all forward migrations (UP)...");
  run(`${pythonCmd} -m packages.agent.scripts.migrate`);
  run("node scripts/migrate.mjs", join(REPO_ROOT, "services", "cosa"));
  run("node scripts/migrate.mjs", join(REPO_ROOT, "services", "company"));
  console.log("✓ Phase 1 complete: All migrations applied.\n");

  // Phase 2: Rollback N steps (Down)
  console.log(`▶ Phase 2: Rolling back ${steps} migrations on each service (DOWN)...`);
  run(`${pythonCmd} -m packages.agent.scripts.migrate --down ${steps}`);
  run(`node scripts/migrate.mjs --down ${steps}`, join(REPO_ROOT, "services", "cosa"));
  run(`node scripts/migrate.mjs --down ${steps}`, join(REPO_ROOT, "services", "company"));
  console.log("✓ Phase 2 complete: Rollback applied successfully.\n");

  // Phase 3: Re-apply forward migrations (Up)
  console.log("▶ Phase 3: Re-applying forward migrations (UP)...");
  run(`${pythonCmd} -m packages.agent.scripts.migrate`);
  run("node scripts/migrate.mjs", join(REPO_ROOT, "services", "cosa"));
  run("node scripts/migrate.mjs", join(REPO_ROOT, "services", "company"));
  console.log("✓ Phase 3 complete: Re-applied forward migrations.\n");

  // Phase 4: Verify schema fingerprint (Gate D)
  console.log("▶ Phase 4: Introspecting schema and verifying against golden fingerprint (Gate D)...");
  run("node scripts/schema-fingerprint.mjs --check");
  console.log("✓ Phase 4 complete: Schema fingerprint matches golden baseline.\n");

  console.log("================================================================================");
  console.log("🎉 Migration Gate E VERIFIED: All .down.sql rollbacks and re-runs are idempotent!");
  console.log("================================================================================\n");
}

main().catch((err) => {
  console.error("\n❌ Migration rollback roundtrip test failed:", err);
  process.exit(1);
});
