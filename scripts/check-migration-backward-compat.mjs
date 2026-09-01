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

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");

// `--dir <path>` cho phép test (tests/quality/test_migration_backward_compat.py)
// trỏ checker vào một thư mục ad-hoc (vd. tmp_path) thay vì quét toàn repo —
// không re-implement logic bằng Python, chỉ đổi phạm vi quét của chính script này.
const argv = process.argv.slice(2);
const dirFlagIndex = argv.indexOf("--dir");
const overrideDir = dirFlagIndex !== -1 ? argv[dirFlagIndex + 1] : null;

const MIGRATION_TARGETS = overrideDir
  ? [{ group: "adhoc", dir: resolve(overrideDir), filter: (f) => f.endsWith(".up.sql") }]
  : [
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

// Sau Task 8: một comment tự phong `allow-destructive` KHÔNG còn đủ để miễn trừ
// destructive DDL — phải trỏ (`evidence=<path>`) tới một file evidence thật,
// tồn tại trên đĩa và có đủ field bắt buộc (xem interface trong task-8-brief).
// CI chỉ verify SYNTAX/PATH tồn tại + field không rỗng — giá trị thật
// (checksum, timestamp) do release operator điền tay trước khi deploy thật.
const EVIDENCE_REF_REGEX = /migration-compat:\s*allow-destructive\s+evidence=(\S+)/;
const REQUIRED_EVIDENCE_FIELDS = [
  "migration",
  "environment",
  "approved_adr",
  "backup_sha256",
  "restore_rehearsal"
];

function resolveEvidencePath(rawPath) {
  if (isAbsolute(rawPath)) return rawPath;
  return join(REPO_ROOT, rawPath);
}

function parseCutoverEvidence(content) {
  const block = content.match(/```yaml\s*\ncutover:\s*\n([\s\S]*?)```/);
  if (!block) return null;
  const fields = {};
  for (const line of block[1].split("\n")) {
    const kv = line.match(/^\s{2}([a-zA-Z0-9_]+):\s*(.+?)\s*$/);
    if (!kv) continue;
    fields[kv[1]] = kv[2].replace(/^['"]|['"]$/g, "");
  }
  return fields;
}

/**
 * Kiểm tra evidence file cho một exemption `allow-destructive`. Trả về mảng
 * lý do lỗi (rỗng nếu hợp lệ) — luôn bắt đầu với "missing cutover evidence"
 * để test/CI có thể grep chung một cụm từ ổn định.
 */
function validateCutoverEvidence(content, relativeName, migrationId) {
  const refMatch = content.match(EVIDENCE_REF_REGEX);
  if (!refMatch) {
    return [
      `missing cutover evidence: '${relativeName}' dùng exemption comment tự do, ` +
        "không có tham chiếu 'evidence=<path>' tới file evidence đã duyệt"
    ];
  }

  const evidencePath = resolveEvidencePath(refMatch[1]);
  if (!existsSync(evidencePath)) {
    return [`missing cutover evidence: file '${refMatch[1]}' không tồn tại trên đĩa`];
  }

  const evidenceContent = readFileSync(evidencePath, "utf-8");
  const fields = parseCutoverEvidence(evidenceContent);
  if (!fields) {
    return [
      `missing cutover evidence: '${refMatch[1]}' không chứa khối YAML 'cutover:' hợp lệ`
    ];
  }

  const missing = REQUIRED_EVIDENCE_FIELDS.filter((key) => !fields[key]);
  if (missing.length > 0) {
    return [`missing cutover evidence: field(s) [${missing.join(", ")}] rỗng hoặc thiếu`];
  }

  if (fields.migration !== migrationId) {
    return [
      `missing cutover evidence: field 'migration' ('${fields.migration}') không khớp migration file '${migrationId}'`
    ];
  }

  if (fields.environment !== "prelaunch-only") {
    return [
      "missing cutover evidence: field 'environment' phải là 'prelaunch-only' tường minh " +
        `(nhận '${fields.environment}')`
    ];
  }

  if (fields.restore_rehearsal !== "passed") {
    return [
      "missing cutover evidence: field 'restore_rehearsal' phải là 'passed' " +
        `(nhận '${fields.restore_rehearsal}')`
    ];
  }

  return [];
}

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
  "agent/017_workspace_only_tenancy.sql",
  // Task 8 (2026-09-02) chỉ hardening evidence-gate cho migration 29
  // (`cosa/29_cleanup_legacy_companies_and_rename_workspaces.up.sql` — xem
  // docs/runbooks/evidence/m2-destructive-cutover-29.md). 4 migration dưới
  // đây đã merge trước Task 8 với free-form `allow-destructive` comment, nằm
  // ngoài phạm vi task này — grandfathered tạm thời để không phá vỡ CI của
  // các thay đổi không liên quan; hardening cho chúng là follow-up riêng.
  "company/finance-legal/25_legal_entity_status_v2.up.sql",
  "company/identity/5_workspace_lifecycle_stage.up.sql",
  "company/operations/24_workspace_stage_lifecycle_rename.up.sql",
  "company/operations/26_project_lifecycle_stage.up.sql"
]);

function checkFile(filePath, relativeName, baseFileName) {
  if (HISTORICAL_EXEMPTIONS.has(relativeName)) {
    return [];
  }

  const content = readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const violations = [];
  const hasFileExemption = content.includes(EXEMPTION_MARKER);
  const migrationId = baseFileName.replace(/\.up\.sql$/, "");

  // Exemption chỉ hợp lệ khi có evidence file thật (Task 8) — tính 1 lần cho
  // cả file, không phải theo từng dòng, vì marker + evidence luôn khai báo ở
  // đầu file.
  const evidenceErrors = hasFileExemption
    ? validateCutoverEvidence(content, relativeName, migrationId)
    : null;

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    // Skip comment-only lines
    if (trimmed.startsWith("--") || trimmed.startsWith("/*") || trimmed.startsWith("*")) {
      return;
    }

    // Check if current line has inline exemption
    if (line.includes(EXEMPTION_MARKER) || hasFileExemption) {
      if (evidenceErrors && evidenceErrors.length > 0) {
        for (const pattern of DESTRUCTIVE_PATTERNS) {
          if (pattern.regex.test(line)) {
            violations.push({
              file: relativeName,
              line: idx + 1,
              code: trimmed,
              rule: pattern.id,
              description: evidenceErrors[0]
            });
          }
        }
      }
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
      const violations = checkFile(fullPath, relativeName, file);
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
