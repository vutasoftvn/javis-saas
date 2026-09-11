#!/usr/bin/env node
/**
 * Authorization Cutover Preflight Check
 * 
 * Verifies that workspaces meet all prerequisites before switching authorization
 * enforcement mode from SHADOW to ENFORCED.
 * 
 * Reports only IDs/counts for:
 * - zero human founder assignment
 * - invalid founder subject
 * - AI member in human-only role
 * - orphan assignment reference
 * - invalid capability binding
 * - expired active grant
 * - missing authorization state
 * 
 * Usage:
 *   node services/company/scripts/authorization-cutover-preflight.mjs --check
 *   node services/company/scripts/authorization-cutover-preflight.mjs --check --workspace 12345
 */

import { Client } from "pg";

function getDatabaseUrl() {
  const url =
    process.env.WORKSPACE_DATABASE_URL ||
    process.env.WORKSPACE_MIGRATOR_DATABASE_URL ||
    process.env.DATABASE_URL;
  return url;
}

function parseArgs() {
  const args = process.argv.slice(2);
  let check = false;
  let workspaceId = null;
  let json = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--check") {
      check = true;
    } else if (arg === "--json") {
      json = true;
    } else if (arg === "--workspace") {
      workspaceId = args[++i];
    } else if (arg.startsWith("--workspace=")) {
      workspaceId = arg.split("=")[1];
    }
  }

  return { check, workspaceId, json };
}

export async function runPreflight(client, options = {}) {
  const { workspaceId } = options;
  const filterClause = workspaceId ? "WHERE w.id = $1" : "";
  const filterParams = workspaceId ? [workspaceId] : [];

  const results = {
    checkedWorkspacesCount: 0,
    cleanWorkspacesCount: 0,
    discrepancies: [],
  };

  // 1. Total workspaces to check
  const wsRes = await client.query(
    `SELECT w.id::text as id FROM core.workspaces w ${filterClause} ORDER BY w.id ASC`,
    filterParams
  );
  results.checkedWorkspacesCount = wsRes.rows.length;

  // 2. Missing authorization state
  const missingStateQuery = workspaceId
    ? `SELECT w.id::text as id FROM core.workspaces w LEFT JOIN core.workspace_authorization_states s ON w.id = s.workspace_id WHERE w.id = $1 AND s.workspace_id IS NULL`
    : `SELECT w.id::text as id FROM core.workspaces w LEFT JOIN core.workspace_authorization_states s ON w.id = s.workspace_id WHERE s.workspace_id IS NULL`;
  const missingStateRes = await client.query(missingStateQuery, filterParams);
  for (const row of missingStateRes.rows) {
    results.discrepancies.push({
      workspaceId: row.id,
      code: "MISSING_AUTHORIZATION_STATE",
      message: "Workspace missing row in core.workspace_authorization_states",
    });
  }

  // 3. Zero human founder assignment
  const zeroFounderQuery = `
    SELECT w.id::text as id FROM core.workspaces w
    ${filterClause}
    ${workspaceId ? "AND" : "WHERE"} NOT EXISTS (
      SELECT 1 FROM core.member_role_assignments mra
      JOIN core.workspace_roles r ON mra.role_id = r.id AND r.workspace_id = w.id
      JOIN core.workforce_members wm ON mra.workforce_member_id = wm.id AND wm.workspace_id = w.id
      WHERE mra.workspace_id = w.id
        AND r.role_key = 'founder'
        AND wm.member_type = 'HUMAN'
        AND wm.status = 'active'
        AND (mra.valid_from IS NULL OR mra.valid_from <= NOW())
        AND (mra.valid_until IS NULL OR mra.valid_until > NOW())
    )
  `;
  const zeroFounderRes = await client.query(zeroFounderQuery, filterParams);
  for (const row of zeroFounderRes.rows) {
    results.discrepancies.push({
      workspaceId: row.id,
      code: "ZERO_HUMAN_FOUNDER_ASSIGNMENT",
      message: "Workspace has zero active HUMAN workforce members with active founder role",
    });
  }

  // 4. Invalid founder subject (AI agent or inactive member in founder role)
  const invalidFounderQuery = `
    SELECT mra.id::text, mra.workspace_id::text, mra.workforce_member_id::text, wm.member_type, wm.status
    FROM core.member_role_assignments mra
    JOIN core.workspace_roles r ON mra.role_id = r.id
    JOIN core.workforce_members wm ON mra.workforce_member_id = wm.id
    WHERE r.role_key = 'founder'
      AND (wm.member_type != 'HUMAN' OR wm.status != 'active')
      ${workspaceId ? "AND mra.workspace_id = $1" : ""}
  `;
  const invalidFounderRes = await client.query(invalidFounderQuery, filterParams);
  for (const row of invalidFounderRes.rows) {
    results.discrepancies.push({
      workspaceId: row.workspace_id,
      code: "INVALID_FOUNDER_SUBJECT",
      workforceMemberId: row.workforce_member_id,
      message: `Founder role assigned to invalid subject (memberType=${row.member_type}, status=${row.status})`,
    });
  }

  // 5. AI member in human-only role
  const aiInHumanRoleQuery = `
    SELECT mra.id::text, mra.workspace_id::text, mra.workforce_member_id::text, r.role_key, r.allowed_member_types
    FROM core.member_role_assignments mra
    JOIN core.workspace_roles r ON mra.role_id = r.id
    JOIN core.workforce_members wm ON mra.workforce_member_id = wm.id
    WHERE wm.member_type = 'AI_AGENT'
      AND NOT ('AI_AGENT' = ANY(r.allowed_member_types))
      ${workspaceId ? "AND mra.workspace_id = $1" : ""}
  `;
  const aiInHumanRoleRes = await client.query(aiInHumanRoleQuery, filterParams);
  for (const row of aiInHumanRoleRes.rows) {
    results.discrepancies.push({
      workspaceId: row.workspace_id,
      code: "AI_IN_HUMAN_ONLY_ROLE",
      workforceMemberId: row.workforce_member_id,
      message: `AI workforce member assigned to human-only role ${row.role_key}`,
    });
  }

  // 6. Orphan assignment reference
  const orphanQuery = `
    SELECT mra.id::text, mra.workspace_id::text, mra.workforce_member_id::text, mra.role_id::text
    FROM core.member_role_assignments mra
    WHERE (
      NOT EXISTS (SELECT 1 FROM core.workforce_members wm WHERE wm.id = mra.workforce_member_id)
      OR NOT EXISTS (SELECT 1 FROM core.workspace_roles r WHERE r.id = mra.role_id)
    )
    ${workspaceId ? "AND mra.workspace_id = $1" : ""}
  `;
  const orphanRes = await client.query(orphanQuery, filterParams);
  for (const row of orphanRes.rows) {
    results.discrepancies.push({
      workspaceId: row.workspace_id,
      code: "ORPHAN_ASSIGNMENT_REFERENCE",
      message: `Role assignment ${row.id} references non-existent member or role`,
    });
  }

  // 7. Invalid capability binding
  const invalidBindingQuery = `
    SELECT g.id::text, g.workspace_id::text, g.capability_id, g.agent_workforce_member_id::text
    FROM core.agent_capability_grants g
    WHERE g.status = 'ACTIVE'
      AND (
        NOT EXISTS (SELECT 1 FROM core.capability_permission_bindings b WHERE b.capability_id = g.capability_id AND b.enabled = true)
        OR NOT EXISTS (SELECT 1 FROM core.workforce_members wm WHERE wm.id = g.agent_workforce_member_id AND wm.member_type = 'AI_AGENT' AND wm.status = 'active')
      )
      ${workspaceId ? "AND g.workspace_id = $1" : ""}
  `;
  const invalidBindingRes = await client.query(invalidBindingQuery, filterParams);
  for (const row of invalidBindingRes.rows) {
    results.discrepancies.push({
      workspaceId: row.workspace_id,
      code: "INVALID_CAPABILITY_BINDING",
      grantId: row.id,
      message: `Grant ${row.id} references invalid/disabled capability binding or inactive/non-AI member`,
    });
  }

  // 8. Expired active grant
  const expiredGrantQuery = `
    SELECT g.id::text, g.workspace_id::text, g.capability_id, g.valid_until
    FROM core.agent_capability_grants g
    WHERE g.status = 'ACTIVE'
      AND g.valid_until IS NOT NULL
      AND g.valid_until <= NOW()
      ${workspaceId ? "AND g.workspace_id = $1" : ""}
  `;
  const expiredGrantRes = await client.query(expiredGrantQuery, filterParams);
  for (const row of expiredGrantRes.rows) {
    results.discrepancies.push({
      workspaceId: row.workspace_id,
      code: "EXPIRED_ACTIVE_GRANT",
      grantId: row.id,
      message: `Grant ${row.id} for ${row.capability_id} is ACTIVE but expired at ${row.valid_until}`,
    });
  }

  const failedWorkspaceIds = new Set(results.discrepancies.map((d) => d.workspaceId));
  results.cleanWorkspacesCount = results.checkedWorkspacesCount - failedWorkspaceIds.size;
  results.isClean = results.discrepancies.length === 0;

  return results;
}

async function main() {
  const { check, workspaceId, json } = parseArgs();

  if (!check) {
    console.log("Usage: node services/company/scripts/authorization-cutover-preflight.mjs --check [--workspace <id>] [--json]");
    process.exit(0);
  }

  const dbUrl = getDatabaseUrl();
  if (!dbUrl) {
    console.error("❌ WORKSPACE_DATABASE_URL or DATABASE_URL environment variable is required.");
    process.exit(1);
  }

  const client = new Client({ connectionString: dbUrl });
  await client.connect();

  try {
    const report = await runPreflight(client, { workspaceId });

    if (json) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      console.log("=== Authorization Cutover Preflight Summary ===");
      console.log(`Checked Workspaces: ${report.checkedWorkspacesCount}`);
      console.log(`Clean Workspaces:   ${report.cleanWorkspacesCount}`);
      console.log(`Discrepancies:      ${report.discrepancies.length}`);

      if (!report.isClean) {
        console.log("\n❌ Preflight failed with discrepancies:");
        for (const d of report.discrepancies) {
          console.log(`  - [${d.code}] Workspace: ${d.workspaceId} | ${d.message}`);
        }
      } else {
        console.log("\n✅ Preflight check passed: all checked workspaces are clean and ready for authorization enforcement.");
      }
    }

    if (!report.isClean) {
      process.exit(1);
    }
    process.exit(0);
  } finally {
    await client.end();
  }
}

// Only execute when run directly
if (process.argv[1] && process.argv[1].endsWith("authorization-cutover-preflight.mjs")) {
  main().catch((err) => {
    console.error("Fatal error during authorization cutover preflight:", err);
    process.exit(1);
  });
}
