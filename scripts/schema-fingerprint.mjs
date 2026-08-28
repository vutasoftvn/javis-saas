#!/usr/bin/env node
/**
 * Migration Gate D — Schema Fingerprint
 *
 * Introspects actual database schemas (tables, columns, types, nullability,
 * defaults, PK/FK, unique constraints, check constraints, indexes, enums)
 * after migrations have run, normalizes metadata into a canonical structure,
 * and generates/verifies SHA-256 fingerprints against deploy/schema/fingerprints.json.
 *
 * Usage:
 *   node scripts/schema-fingerprint.mjs --check   (Fail and print diff if drifted)
 *   node scripts/schema-fingerprint.mjs --write   (Update golden snapshots)
 */

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const GOLDEN_PATH = join(REPO_ROOT, "deploy", "schema", "fingerprints.json");

// Dynamic import for 'pg' module to work seamlessly from any location
let pg;
try {
  pg = await import("pg");
} catch {
  try {
    pg = await import("../services/cosa/node_modules/pg/lib/index.js");
  } catch {
    pg = await import("../services/company/node_modules/pg/lib/index.js");
  }
}
const { Client } = pg.default || pg;

const SCHEMA_GROUPS = {
  agent_core: {
    name: "agent_core",
    envUrlKey: "AGENT_CORE_DATABASE_URL",
    fallbackEnvKey: "DATABASE_URL",
    defaultUrl: "postgresql://javis:javis@127.0.0.1:5432/javis",
    schemas: [
      "agent_artifact",
      "agent_conversation",
      "agent_core",
      "agent_core_governance",
      "agent_evals",
      "agent_memory",
      "agent_registry",
      "knowledge",
      "events"
    ]
  },
  cosa: {
    name: "cosa",
    envUrlKey: "COSA_DATABASE_URL",
    fallbackEnvKey: "CONTROL_PLANE_DATABASE_URL",
    defaultUrl: "postgresql://cosa:cosa@127.0.0.1:5432/cosa",
    schemas: [
      "cosa",
      "control_plane"
    ]
  },
  company: {
    name: "company",
    envUrlKey: "COMPANY_DATABASE_URL",
    fallbackEnvKey: "DATABASE_URL",
    defaultUrl: "postgresql://cosa:cosa@127.0.0.1:5433/company",
    schemas: [
      "commercial",
      "core",
      "finance",
      "integration",
      "legal",
      "operating",
      "sales",
      "strategy",
      "validation",
      "engagement"
    ]
  }
};

function resolveDatabaseUrl(group) {
  let url =
    process.env[group.envUrlKey] ||
    (group.fallbackEnvKey ? process.env[group.fallbackEnvKey] : null) ||
    process.env.DATABASE_URL ||
    group.defaultUrl;

  // Handle SQLAlchemy async scheme: postgresql+asyncpg:// -> postgresql://
  if (url.startsWith("postgresql+asyncpg://")) {
    url = url.replace("postgresql+asyncpg://", "postgresql://");
  }
  return url;
}

function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

function normalizeDefault(def) {
  if (!def) return null;
  return def.trim().replace(/\s+/g, " ");
}

function normalizeIndexDef(def) {
  if (!def) return "";
  return def.trim().replace(/\s+/g, " ");
}

async function introspectGroupSchema(groupConfig) {
  const url = resolveDatabaseUrl(groupConfig);
  const client = new Client({ connectionString: url });
  await client.connect();

  try {
    // 1. Discover which configured schemas actually exist in this database
    const schemaRes = await client.query(
      `
      SELECT nspname AS schema_name
      FROM pg_namespace
      WHERE nspname = ANY($1)
      ORDER BY nspname;
      `,
      [groupConfig.schemas]
    );
    const existingSchemas = schemaRes.rows.map((r) => r.schema_name);

    if (existingSchemas.length === 0) {
      return {
        schemas: [],
        tables_count: 0,
        enums: [],
        tables: {}
      };
    }

    // 2. Custom Enums
    const enumRes = await client.query(
      `
      SELECT
        n.nspname AS schema_name,
        t.typname AS enum_name,
        e.enumlabel AS enum_value,
        e.enumsortorder AS sort_order
      FROM pg_type t
      JOIN pg_enum e ON t.oid = e.enumtypid
      JOIN pg_namespace n ON n.oid = t.typnamespace
      WHERE n.nspname = ANY($1)
      ORDER BY n.nspname, t.typname, e.enumsortorder;
      `,
      [existingSchemas]
    );

    const enumMap = {};
    for (const row of enumRes.rows) {
      const key = `${row.schema_name}.${row.enum_name}`;
      if (!enumMap[key]) {
        enumMap[key] = {
          schema: row.schema_name,
          name: row.enum_name,
          values: []
        };
      }
      enumMap[key].values.push(row.enum_value);
    }
    const enums = Object.keys(enumMap)
      .sort()
      .map((k) => enumMap[k]);

    // 3. Tables & Views
    const tableRes = await client.query(
      `
      SELECT
        table_schema,
        table_name,
        table_type
      FROM information_schema.tables
      WHERE table_schema = ANY($1)
      ORDER BY table_schema, table_name;
      `,
      [existingSchemas]
    );

    // 4. Columns
    const colRes = await client.query(
      `
      SELECT
        table_schema,
        table_name,
        column_name,
        ordinal_position,
        column_default,
        is_nullable,
        data_type,
        udt_name,
        character_maximum_length,
        numeric_precision,
        numeric_scale
      FROM information_schema.columns
      WHERE table_schema = ANY($1)
      ORDER BY table_schema, table_name, ordinal_position;
      `,
      [existingSchemas]
    );

    const columnsByTable = {};
    for (const col of colRes.rows) {
      const tableKey = `${col.table_schema}.${col.table_name}`;
      if (!columnsByTable[tableKey]) {
        columnsByTable[tableKey] = [];
      }
      columnsByTable[tableKey].push({
        name: col.column_name,
        type: col.data_type,
        udt: col.udt_name,
        nullable: col.is_nullable === "YES",
        default: normalizeDefault(col.column_default),
        max_length: col.character_maximum_length,
        precision: col.numeric_precision,
        scale: col.numeric_scale
      });
    }

    // 5. PK and Unique Constraints
    const constraintRes = await client.query(
      `
      SELECT
        tc.table_schema,
        tc.table_name,
        tc.constraint_name,
        tc.constraint_type,
        kcu.column_name,
        kcu.ordinal_position
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
        AND tc.table_name = kcu.table_name
      WHERE tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        AND tc.table_schema = ANY($1)
      ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position;
      `,
      [existingSchemas]
    );

    const pkByTable = {};
    const uniqueByTable = {};
    for (const row of constraintRes.rows) {
      const tableKey = `${row.table_schema}.${row.table_name}`;
      if (row.constraint_type === "PRIMARY KEY") {
        if (!pkByTable[tableKey]) {
          pkByTable[tableKey] = {
            name: row.constraint_name,
            columns: []
          };
        }
        pkByTable[tableKey].columns.push(row.column_name);
      } else if (row.constraint_type === "UNIQUE") {
        if (!uniqueByTable[tableKey]) {
          uniqueByTable[tableKey] = {};
        }
        if (!uniqueByTable[tableKey][row.constraint_name]) {
          uniqueByTable[tableKey][row.constraint_name] = {
            name: row.constraint_name,
            columns: []
          };
        }
        uniqueByTable[tableKey][row.constraint_name].columns.push(row.column_name);
      }
    }

    // 6. Foreign Keys
    const fkRes = await client.query(
      `
      SELECT
        tc.table_schema,
        tc.table_name,
        tc.constraint_name,
        kcu.column_name,
        kcu.ordinal_position,
        ccu.table_schema AS foreign_table_schema,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        rc.update_rule,
        rc.delete_rule
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
      JOIN information_schema.constraint_column_usage ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
      JOIN information_schema.referential_constraints rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
      WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = ANY($1)
      ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position;
      `,
      [existingSchemas]
    );

    const fkByTable = {};
    for (const row of fkRes.rows) {
      const tableKey = `${row.table_schema}.${row.table_name}`;
      if (!fkByTable[tableKey]) {
        fkByTable[tableKey] = {};
      }
      if (!fkByTable[tableKey][row.constraint_name]) {
        fkByTable[tableKey][row.constraint_name] = {
          name: row.constraint_name,
          columns: [],
          foreign_table: `${row.foreign_table_schema}.${row.foreign_table_name}`,
          foreign_columns: [],
          on_update: row.update_rule,
          on_delete: row.delete_rule
        };
      }
      if (!fkByTable[tableKey][row.constraint_name].columns.includes(row.column_name)) {
        fkByTable[tableKey][row.constraint_name].columns.push(row.column_name);
      }
      if (!fkByTable[tableKey][row.constraint_name].foreign_columns.includes(row.foreign_column_name)) {
        fkByTable[tableKey][row.constraint_name].foreign_columns.push(row.foreign_column_name);
      }
    }

    // 7. Check Constraints
    const checkRes = await client.query(
      `
      SELECT
        tc.table_schema,
        tc.table_name,
        tc.constraint_name,
        cc.check_clause
      FROM information_schema.table_constraints tc
      JOIN information_schema.check_constraints cc
        ON tc.constraint_name = cc.constraint_name
        AND tc.constraint_schema = cc.constraint_schema
      WHERE tc.constraint_type = 'CHECK'
        AND tc.table_schema = ANY($1)
        AND cc.check_clause NOT LIKE '%IS NOT NULL'
      ORDER BY tc.table_schema, tc.table_name, tc.constraint_name;
      `,
      [existingSchemas]
    );

    const checkByTable = {};
    for (const row of checkRes.rows) {
      const tableKey = `${row.table_schema}.${row.table_name}`;
      if (!checkByTable[tableKey]) {
        checkByTable[tableKey] = [];
      }
      checkByTable[tableKey].push({
        name: row.constraint_name,
        clause: normalizeDefault(row.check_clause)
      });
    }

    // 8. Indexes
    const indexRes = await client.query(
      `
      SELECT
        schemaname AS table_schema,
        tablename AS table_name,
        indexname,
        indexdef
      FROM pg_indexes
      WHERE schemaname = ANY($1)
      ORDER BY schemaname, tablename, indexname;
      `,
      [existingSchemas]
    );

    const indexByTable = {};
    for (const row of indexRes.rows) {
      const tableKey = `${row.table_schema}.${row.table_name}`;
      if (!indexByTable[tableKey]) {
        indexByTable[tableKey] = [];
      }
      indexByTable[tableKey].push({
        name: row.indexname,
        definition: normalizeIndexDef(row.indexdef)
      });
    }

    // 9. Assemble tables structure
    const tables = {};
    for (const t of tableRes.rows) {
      const tableKey = `${t.table_schema}.${t.table_name}`;
      const uniqueList = uniqueByTable[tableKey]
        ? Object.keys(uniqueByTable[tableKey])
            .sort()
            .map((k) => uniqueByTable[tableKey][k])
        : [];
      const fkList = fkByTable[tableKey]
        ? Object.keys(fkByTable[tableKey])
            .sort()
            .map((k) => fkByTable[tableKey][k])
        : [];

      tables[tableKey] = {
        schema: t.table_schema,
        name: t.table_name,
        type: t.table_type,
        columns: columnsByTable[tableKey] || [],
        primary_key: pkByTable[tableKey] || null,
        unique_constraints: uniqueList,
        foreign_keys: fkList,
        check_constraints: checkByTable[tableKey] || [],
        indexes: indexByTable[tableKey] || []
      };
    }

    return {
      schemas: existingSchemas,
      tables_count: Object.keys(tables).length,
      enums,
      tables
    };
  } finally {
    await client.end();
  }
}

function canonicalJsonStringify(obj) {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map((item) => canonicalJsonStringify(item)).join(",") + "]";
  }
  const sortedKeys = Object.keys(obj).sort();
  const pairs = sortedKeys.map((key) => `${JSON.stringify(key)}:${canonicalJsonStringify(obj[key])}`);
  return "{" + pairs.join(",") + "}";
}

async function collectAllFingerprints() {
  const result = {
    version: 1,
    generated_at: new Date().toISOString(),
    groups: {}
  };

  for (const [groupKey, groupConfig] of Object.entries(SCHEMA_GROUPS)) {
    const data = await introspectGroupSchema(groupConfig);
    const canonicalGroupStr = canonicalJsonStringify({
      schemas: data.schemas,
      enums: data.enums,
      tables: data.tables
    });
    const fp = sha256(canonicalGroupStr);

    result.groups[groupKey] = {
      fingerprint: fp,
      schemas: data.schemas,
      tables_count: data.tables_count,
      enums: data.enums,
      tables: data.tables
    };
  }

  return result;
}

function diffTables(currentTables, goldenTables) {
  const diffs = [];
  const currentKeys = new Set(Object.keys(currentTables));
  const goldenKeys = new Set(Object.keys(goldenTables));

  for (const k of [...currentKeys].sort()) {
    if (!goldenKeys.has(k)) {
      diffs.push(`  + Table added: ${k}`);
    }
  }
  for (const k of [...goldenKeys].sort()) {
    if (!currentKeys.has(k)) {
      diffs.push(`  - Table removed: ${k}`);
    }
  }

  for (const k of [...currentKeys].sort()) {
    if (goldenKeys.has(k)) {
      const curT = currentTables[k];
      const golT = goldenTables[k];
      const curStr = JSON.stringify(curT);
      const golStr = JSON.stringify(golT);
      if (curStr !== golStr) {
        diffs.push(`  ~ Table structure changed: ${k}`);
        // Diff columns
        const curCols = new Set(curT.columns.map((c) => c.name));
        const golCols = new Set(golT.columns.map((c) => c.name));
        for (const c of curCols) {
          if (!golCols.has(c)) diffs.push(`      + Column added: ${c}`);
        }
        for (const c of golCols) {
          if (!curCols.has(c)) diffs.push(`      - Column removed: ${c}`);
        }
      }
    }
  }

  return diffs;
}

async function main() {
  const isWrite = process.argv.includes("--write");
  const isCheck = process.argv.includes("--check") || !isWrite;

  console.log("🔍 Introspecting database schemas across groups (agent_core, cosa, company)...");
  const current = await collectAllFingerprints();

  if (isWrite) {
    mkdirSync(dirname(GOLDEN_PATH), { recursive: true });
    writeFileSync(GOLDEN_PATH, JSON.stringify(current, null, 2) + "\n", "utf-8");
    console.log(`✅ Golden schema fingerprints written to: ${GOLDEN_PATH}`);
    for (const [gk, g] of Object.entries(current.groups)) {
      console.log(`   [${gk}] tables: ${g.tables_count}, fingerprint: ${g.fingerprint}`);
    }
    return;
  }

  if (isCheck) {
    if (!existsSync(GOLDEN_PATH)) {
      console.error(`❌ Golden file not found at: ${GOLDEN_PATH}`);
      console.error("   Run 'make schema-fingerprint-write' (or 'node scripts/schema-fingerprint.mjs --write') to create it.");
      process.exit(1);
    }

    const golden = JSON.parse(readFileSync(GOLDEN_PATH, "utf-8"));
    let hasMismatch = false;

    console.log("Comparing current schema fingerprints with golden snapshot...\n");

    for (const [groupKey, groupConfig] of Object.entries(SCHEMA_GROUPS)) {
      const curGroup = current.groups[groupKey];
      const golGroup = golden.groups ? golden.groups[groupKey] : null;

      if (!golGroup) {
        console.error(`❌ Group '${groupKey}' missing from golden fingerprints!`);
        hasMismatch = true;
        continue;
      }

      if (curGroup.fingerprint !== golGroup.fingerprint) {
        hasMismatch = true;
        console.error(`❌ Schema fingerprint MISMATCH for group '${groupKey}':`);
        console.error(`   Current: ${curGroup.fingerprint}`);
        console.error(`   Golden:  ${golGroup.fingerprint}`);
        const diffs = diffTables(curGroup.tables, golGroup.tables);
        if (diffs.length > 0) {
          console.error("   Diff details:");
          diffs.forEach((d) => console.error(d));
        }
        console.error("");
      } else {
        console.log(`✓ [${groupKey}] fingerprint MATCH (${curGroup.fingerprint}, ${curGroup.tables_count} tables)`);
      }
    }

    if (hasMismatch) {
      console.error("\n❌ Migration Gate D failed: Schema drift detected!");
      console.error("   If these schema changes were intentional, update the golden file via:");
      console.error("     make schema-fingerprint-write");
      console.error("   and commit deploy/schema/fingerprints.json with your migration changes.");
      process.exit(1);
    }

    console.log("\n✅ Migration Gate D passed: All schema fingerprints match golden baseline.");
  }
}

main().catch((err) => {
  console.error("❌ Schema fingerprint error:", err);
  process.exit(1);
});
