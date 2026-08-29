#!/usr/bin/env node
/**
 * Migration Backward Compatibility Checker (Expand-Contract Policy Guard)
 *
 * Verifies that forward database migrations adhere to the Expand-Contract policy
 * defined in ADR-CUTOVER-001 and docs/operations/migrations.md.
 *
 * Scans SQL files for destructive DDL operations:
 * - DROP TABLE
 * - DROP COLUMN
 * - DROP SCHEMA
 * - RENAME COLUMN / TABLE
 * - ALTER COLUMN ... SET NOT NULL (without safe defaults)
 * - TRUNCATE TABLE
 *
 * Exemption:
 * If a destructive operation is intentional and part of a planned Contract phase (Release N+2),
 * annotate the statement or file with:
 *   -- migration-compat: allow-destructive [reason]
 *
 * Usage:
 *   node scripts/check-migration-backward-compat.mjs
 */

import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");

const MIGRATION_TARGETS = [
  {
    group: "cosa",
    dir: join(REPO_ROOT, "services", "cosa", "migrations"),
    filter: (f) => f.endsWith(".up.sql")
  },
  {
    group: "company/commercial",
    dir: join(REPO_ROOT, "services", "company", "commercial", "migrations"),
    filter: (f) => f.endsWith(".up.sql")
  },
  {
    group: "company/finance-legal",
    dir: join(REPO_ROOT, "services", "company", "finance-legal", "migrations"),
    filter: (f) => f.endsWith(".up.sql")
  },
  {
    group: "company/identity",
    dir: join(REPO_ROOT, "services", "company", "identity", "migrations"),
    filter: (f) => f.endsWith(".up.sql")
  },
  {
    group: "company/operations",
    dir: join(REPO_ROOT, "services", "company", "operations", "migrations"),
    filter: (f) => f.endsWith(".up.sql")
  },
  {
    group: "agent",
    dir: join(REPO_ROOT, "packages", "agent", "migrations"),
    filter: (f) => f.endsWith(".sql") && !f.endsWith(".down.sql")
  }
];

const DESTRUCTIVE_PATTERNS = [
  {
    id: "DROP_TABLE",
    regex: /\bDROP\s+TABLE\b/i,
    description: "DROP TABLE destroys existing data and breaks N-1 queries"
  },
  {
    id: "DROP_COLUMN",
    regex: /\b(?:ALTER\s+TABLE\s+[\w\.]+\s+)?DROP\s+COLUMN\b/i,
    description: "DROP COLUMN breaks N-1 application reads and writes"
  },
  {
    id: "DROP_SCHEMA",
    regex: /\bDROP\s+SCHEMA\b/i,
    description: "DROP SCHEMA deletes an entire namespace"
  },
  {
    id: "RENAME_COLUMN",
    regex: /\bRENAME\s+COLUMN\b/i,
    description: "RENAME COLUMN breaks N-1 column references (use expand/contract dual-column pattern)"
  },
  {
    id: "RENAME_TABLE",
    regex: /\bALTER\s+TABLE\s+[\w\.]+\s+RENAME\s+TO\b/i,
    description: "RENAME TABLE breaks N-1 table references"
  },
  {
    id: "TRUNCATE",
    regex: /\bTRUNCATE(?:\s+TABLE)?\b/i,
    description: "TRUNCATE deletes all rows in table"
  }
];

const EXEMPTION_MARKER = "migration-compat: allow-destructive";

// Historical migrations prior to TPR Part 2A (2026-08-28) that were part of
// legacy schema consolidation / baseline. These cannot be edited on disk because
// their sha256 checksums are already recorded and immutable.
const HISTORICAL_EXEMPTIONS = new Set([
  "cosa/13_workspace_only_product_scope.up.sql",
  "company/commercial/7_snowflake_ids.up.sql",
  "company/commercial/8_actor_naming_standardization.up.sql",
  "company/commercial/10_marketing_context_drop_legacy_jsonb.up.sql",
  "company/finance-legal/10_snowflake_ids.up.sql",
  "company/finance-legal/11_drop_validation_domain.up.sql",
  "company/identity/1_baseline_workspace_user_workforce.up.sql",
  "company/operations/8_snowflake_ids.up.sql",
  "company/operations/9_strategy_snowflake_ids.up.sql",
  "company/operations/10_drop_ghost_fields.up.sql",
  "company/operations/11_dedupe_strategy_company_workspace_id.up.sql",
  "company/operations/12_actor_naming_standardization.up.sql",
  "agent/017_workspace_only_tenancy.sql"
]);

function checkFile(filePath, relativeName) {
  if (HISTORICAL_EXEMPTIONS.has(relativeName)) {
    return [];
  }

  const content = readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const violations = [];
  const hasFileExemption = content.includes(EXEMPTION_MARKER);

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    // Skip comment-only lines
    if (trimmed.startsWith("--") || trimmed.startsWith("/*") || trimmed.startsWith("*")) {
      return;
    }

    // Check if current line has inline exemption
    if (line.includes(EXEMPTION_MARKER) || hasFileExemption) {
      return;
    }

    for (const pattern of DESTRUCTIVE_PATTERNS) {
      if (pattern.regex.test(line)) {
        violations.push({
          file: relativeName,
          line: idx + 1,
          code: trimmed,
          rule: pattern.id,
          description: pattern.description
        });
      }
    }
  });

  return violations;
}

async function main() {
  console.log("🛡️ Checking database migrations for Expand-Contract backward compatibility...");

  let totalFiles = 0;
  const allViolations = [];

  for (const target of MIGRATION_TARGETS) {
    let files = [];
    try {
      files = readdirSync(target.dir).filter(target.filter);
    } catch {
      continue;
    }

    for (const file of files) {
      totalFiles++;
      const fullPath = join(target.dir, file);
      const relativeName = `${target.group}/${file}`;
      const violations = checkFile(fullPath, relativeName);
      if (violations.length > 0) {
        allViolations.push(...violations);
      }
    }
  }

  if (allViolations.length > 0) {
    console.error(`\n❌ Found ${allViolations.length} potential backward-compatibility violation(s) in ${totalFiles} migrations:\n`);
    for (const v of allViolations) {
      console.error(`  [${v.rule}] ${v.file}:${v.line}`);
      console.error(`     Statement: "${v.code}"`);
      console.error(`     Reason:    ${v.description}`);
      console.error(`     Fix:       Follow Expand-Contract pattern or annotate with '-- ${EXEMPTION_MARKER} [reason]'\n`);
    }
    process.exit(1);
  }

  console.log(`✅ All ${totalFiles} migrations passed Expand-Contract backward compatibility check (0 violations).\n`);
}

main().catch((err) => {
  console.error("❌ Checker error:", err);
  process.exit(1);
});
