// Fail-closed parsing + precondition validation cho `make test-db-reset`.
//
// Lệnh reset CHỈ dành cho môi trường test: nó tái tạo đúng ba database test
// disposable (javis_agent_test, javis_cosa_test, javis_workspace_test) từ các
// migration baseline 001 Founder Trial. Mọi kiểm tra an toàn ở đây phải chạy
// TRƯỚC khi mở bất kỳ kết nối phá huỷ nào (xem spec §7.2).
//
// Ranh giới cứng: không xoá nguyên database, không xoá schema public, không
// drop-owned-by trên vai trò PUBLIC, không thao tác volume, không xoá file qua
// shell, và không dựng SQL identifier từ biến môi trường. Chỉ dọn object thuộc
// đúng migrator role cố định của từng plane.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

// Repo has no root package.json; `pg` lives in the service workspaces. Resolve
// it from services/company for the reset's own DDL connection.
const _require = createRequire(
  fileURLToPath(new URL("../services/company/package.json", import.meta.url))
);

// Immutable target metadata. Thứ tự cột:
//   plane, databaseName, migratorEnvKey, applicationEnvKey, migratorRole,
//   migrateCommand[], cwd
export const TEST_RESET_TARGETS = [
  [
    "agent",
    "javis_agent_test",
    "AGENT_TEST_MIGRATOR_DATABASE_URL",
    "AGENT_TEST_DATABASE_URL",
    "agent_migrator",
    [process.env.PYTHON || ".venv/bin/python", "-m", "packages.agent.scripts.migrate"],
    ".",
  ],
  [
    "cosa",
    "javis_cosa_test",
    "COSA_TEST_MIGRATOR_DATABASE_URL",
    "COSA_TEST_DATABASE_URL",
    "cosa_migrator",
    ["node", "scripts/migrate.mjs"],
    "services/cosa",
  ],
  [
    "workspace",
    "javis_workspace_test",
    "WORKSPACE_TEST_MIGRATOR_DATABASE_URL",
    "WORKSPACE_TEST_DATABASE_URL",
    "workspace_migrator",
    ["node", "scripts/migrate.mjs"],
    "services/company",
  ],
];

export const RESET_CONFIRMATION = "CONFIRM_FOUNDER_TRIAL_MVP_RESET";
export const RESET_APP_ENV = "test";

// Các biến URL non-test mà lệnh reset TUYỆT ĐỐI không được trùng.
const NON_TEST_URL_ENV_KEYS = [
  "AGENT_DATABASE_URL",
  "AGENT_MIGRATOR_DATABASE_URL",
  "COSA_DATABASE_URL",
  "COSA_MIGRATOR_DATABASE_URL",
  "WORKSPACE_DATABASE_URL",
  "WORKSPACE_MIGRATOR_DATABASE_URL",
];

/**
 * Chuẩn hoá một Postgres URL thành tuple {host, port, database} để so sánh.
 * Chấp nhận scheme dạng `postgresql://` và `postgresql+asyncpg://`.
 */
export function normalizePostgresUrl(rawUrl, envKeyForError) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error(
      `${envKeyForError || "database URL"} is not a valid URL: ${rawUrl}`
    );
  }
  const host = (url.hostname || "").toLowerCase();
  const port = url.port ? Number(url.port) : 5432;
  const database = decodeURIComponent((url.pathname || "").replace(/^\//, ""));
  if (!host || !database) {
    throw new Error(
      `${envKeyForError || "database URL"} is missing host or database name: ${rawUrl}`
    );
  }
  return { host, port, database };
}

function tupleKey({ host, port, database }) {
  return `${host}:${port}/${database}`;
}

/**
 * Đọc ba biến *_TEST_MIGRATOR_DATABASE_URL bắt buộc và dựng danh sách
 * ResetTarget. Ném lỗi ngay nếu thiếu bất kỳ biến nào — không có fallback sang
 * URL non-test.
 */
export function parseResetTargets(env) {
  return TEST_RESET_TARGETS.map((row) => {
    const [
      plane,
      databaseName,
      migratorEnvKey,
      applicationEnvKey,
      migratorRole,
      migrateCommand,
      cwd,
    ] = row;

    const migratorUrl = env[migratorEnvKey];
    if (!migratorUrl || !migratorUrl.trim()) {
      throw new Error(
        `Missing required test migrator URL ${migratorEnvKey} for plane ${plane}`
      );
    }
    const applicationUrl = env[applicationEnvKey] || null;
    const normalized = normalizePostgresUrl(migratorUrl, migratorEnvKey);

    return {
      plane,
      databaseName,
      migratorEnvKey,
      applicationEnvKey,
      migratorUrl,
      applicationUrl,
      migratorRole,
      migrateCommand: [...migrateCommand],
      cwd,
      normalized,
    };
  });
}

/**
 * Xác thực TẤT CẢ điều kiện an toàn trước khi cho phép DDL phá huỷ.
 * Bất kỳ vi phạm nào => ném lỗi, không side effect.
 */
export function assertResetPreconditions(env, targets) {
  // 1. APP_ENV phải đúng bằng "test".
  if (env.APP_ENV !== RESET_APP_ENV) {
    throw new Error(
      `Refusing test-db-reset: APP_ENV=test is required, got APP_ENV=${
        env.APP_ENV ?? "(unset)"
      }`
    );
  }

  // 2. Cụm xác nhận phải đúng chính xác (không cho khoảng trắng thừa).
  if (env.TEST_DATABASE_RESET !== RESET_CONFIRMATION) {
    throw new Error(
      `Refusing test-db-reset: TEST_DATABASE_RESET must equal ${RESET_CONFIRMATION}`
    );
  }

  // 3. Mỗi URL phải trỏ đúng tên database mong đợi.
  for (const target of targets) {
    if (target.normalized.database !== target.databaseName) {
      throw new Error(
        `Refusing test-db-reset: ${target.migratorEnvKey} must point at database ` +
          `${target.databaseName}, got ${target.normalized.database}`
      );
    }
  }

  // 4. Ba tuple host/port/database phải phân biệt theo database.
  const seen = new Map();
  for (const target of targets) {
    const key = tupleKey(target.normalized);
    if (seen.has(key)) {
      throw new Error(
        `Refusing test-db-reset: ${target.migratorEnvKey} and ${seen.get(
          key
        )} resolve to the same host/port/database tuple; targets must be distinct`
      );
    }
    seen.set(key, target.migratorEnvKey);
  }
  const distinctDbs = new Set(targets.map((t) => t.normalized.database));
  if (distinctDbs.size !== targets.length) {
    throw new Error(
      "Refusing test-db-reset: the three target database names must be distinct"
    );
  }

  // 5. Không URL nào được trùng (theo tuple chuẩn hoá) với bất kỳ URL non-test
  //    nào được định nghĩa trong môi trường.
  const nonTestTuples = new Map();
  for (const key of NON_TEST_URL_ENV_KEYS) {
    const raw = env[key];
    if (!raw || !raw.trim()) continue;
    try {
      nonTestTuples.set(tupleKey(normalizePostgresUrl(raw, key)), key);
    } catch {
      // URL non-test không hợp lệ không phải lỗi của lệnh reset; bỏ qua.
    }
  }
  for (const target of targets) {
    const hit = nonTestTuples.get(tupleKey(target.normalized));
    if (hit) {
      throw new Error(
        `Refusing test-db-reset: ${target.migratorEnvKey} resolves to the same ` +
          `database as the non-test URL ${hit}`
      );
    }
  }

  return true;
}

// ── Destructive execution (chỉ chạy sau khi assertResetPreconditions pass) ──

// Tên schema hệ thống không bao giờ bị đụng tới.
const SYSTEM_SCHEMAS = new Set(["public", "information_schema"]);

function advisoryLockKeys(plane) {
  const digest = createHash("sha256")
    .update(`founder-trial-test-reset:${plane}`)
    .digest();
  // Hai khoá int4 signed cho pg_advisory_lock(int4, int4).
  return [digest.readInt32BE(0), digest.readInt32BE(4)];
}

function isSafeRoleIdent(role) {
  return /^[a-z_][a-z0-9_]*$/.test(role);
}

/**
 * Tái tạo một plane test duy nhất. `pgClientFactory` cho phép test tiêm client
 * giả; production dùng `pg.Client`.
 */
export async function resetPlane(target, { pgClientFactory, runMigration } = {}) {
  if (!isSafeRoleIdent(target.migratorRole)) {
    // Role đến từ hằng số metadata, không từ env — nhưng vẫn chặn cứng.
    throw new Error(`Unsafe migrator role identifier: ${target.migratorRole}`);
  }

  const makeClient =
    pgClientFactory ||
    (async () => {
      const { Client } = _require("pg");
      return new Client({ connectionString: target.migratorUrl });
    });

  const client = await makeClient(target);
  await client.connect();
  try {
    // 1. current_database() phải đúng bằng tên mong đợi.
    const dbRes = await client.query("SELECT current_database() AS db");
    const actualDb = dbRes.rows[0]?.db;
    if (actualDb !== target.databaseName) {
      throw new Error(
        `Plane ${target.plane}: connected to ${actualDb}, expected ${target.databaseName}`
      );
    }

    // 2. Một advisory lock cho mỗi plane.
    const [k1, k2] = advisoryLockKeys(target.plane);
    await client.query("SELECT pg_advisory_lock($1, $2)", [k1, k2]);

    try {
      // 3. Mọi schema non-system phải thuộc sở hữu của migrator role mong đợi.
      const owners = await client.query(
        `SELECT n.nspname AS schema_name, r.rolname AS owner
           FROM pg_namespace n
           JOIN pg_roles r ON r.oid = n.nspowner
          WHERE n.nspname NOT IN ('public', 'information_schema')
            AND n.nspname NOT LIKE 'pg_%'`
      );
      for (const row of owners.rows) {
        if (row.owner !== target.migratorRole) {
          throw new Error(
            `Plane ${target.plane}: schema ${row.schema_name} is owned by ` +
              `${row.owner}, expected ${target.migratorRole}; refusing to drop`
          );
        }
      }

      // 4. Drop mọi object thuộc migrator role.
      await client.query(`DROP OWNED BY ${target.migratorRole} CASCADE`);

      // 5. Drop các schema non-system còn sót lại thuộc role đó.
      const remaining = await client.query(
        `SELECT quote_ident(n.nspname) AS ident
           FROM pg_namespace n
           JOIN pg_roles r ON r.oid = n.nspowner
          WHERE r.rolname = $1
            AND n.nspname NOT IN ('public', 'information_schema')
            AND n.nspname NOT LIKE 'pg_%'`,
        [target.migratorRole]
      );
      for (const row of remaining.rows) {
        if (SYSTEM_SCHEMAS.has(row.ident)) continue;
        await client.query(`DROP SCHEMA ${row.ident} CASCADE`);
      }

      // 6. Khôi phục trạng thái an toàn cho schema public + xoá ledger
      //    (đối tượng do application sở hữu).
      await client.query("REVOKE CREATE ON SCHEMA public FROM PUBLIC");
      await client.query("DROP TABLE IF EXISTS public.schema_migrations");

      // Extension trong public (kể cả vector) được giữ nguyên — không đụng tới.
    } finally {
      await client.query("SELECT pg_advisory_unlock($1, $2)", [k1, k2]);
    }
  } finally {
    await client.end();
  }

  // 7. Chạy migration baseline của plane này qua runner hiện có.
  const migrate = runMigration || defaultRunMigration;
  migrate(target);
}

function defaultRunMigration(target) {
  const [cmd, ...args] = target.migrateCommand;
  const result = spawnSync(cmd, args, {
    cwd: target.cwd,
    stdio: "inherit",
    env: {
      ...process.env,
      // Runner hiện có đọc biến non-test; ánh xạ URL test vào đúng tên nó chờ.
      [target.migratorEnvKey.replace("_TEST_", "_")]: target.migratorUrl,
    },
  });
  if (result.status !== 0) {
    throw new Error(
      `Plane ${target.plane}: migration command failed (exit ${result.status})`
    );
  }
}

/**
 * Orchestrator: validate → reset Agent → COSA → Company, dừng ngay khi một
 * plane lỗi và báo rõ plane nào.
 */
export async function runTestDatabaseReset(env, hooks = {}) {
  const targets = parseResetTargets(env);
  assertResetPreconditions(env, targets);

  for (const target of targets) {
    try {
      await resetPlane(target, hooks);
      // eslint-disable-next-line no-console
      console.log(`[test-db-reset] plane ${target.plane}: reset + baseline ok`);
    } catch (err) {
      throw new Error(
        `[test-db-reset] stopped at plane ${target.plane}: ${err.message}`
      );
    }
  }
  return targets.map((t) => t.plane);
}
