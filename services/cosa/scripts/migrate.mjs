#!/usr/bin/env node
// Migration runner thủ công cho app `cosa`.
//
// Vì db.ts dùng thẳng `pg.Pool` (không còn qua encore.dev/storage/sqldb's
// SQLDatabase), Encore không còn tự động áp migrations/*.up.sql nữa — script
// này thay thế việc đó. Chạy:
//   node scripts/migrate.mjs
// hoặc qua `docker compose run --rm migrate-cosa` (xem deploy/central_vps/docker-compose.yaml).
//
// Idempotent: track migration đã áp trong bảng public.schema_migrations
// (khóa chính (service, filename)) để chạy lại nhiều lần không bị lỗi.
//
// Checksum: mỗi migration đã applied lưu kèm sha256 nội dung file. Nếu chạy
// lại mà (service, filename) đã applied nhưng SHA hiện tại khác — FAIL HARD
// (DB_FINAL_CUTOVER.md §5.2), không âm thầm bỏ qua hay ghi đè. Migration
// applied trước khi bật checksum (sha256 NULL) được backfill từ nội dung
// hiện tại trên đĩa ở lần chạy đầu tiên sau khi nâng cấp.
import { Client } from "pg";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const DATABASE_URL =
  process.env.COSA_DATABASE_URL ||
  process.env.CONTROL_PLANE_DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error("COSA_DATABASE_URL or CONTROL_PLANE_DATABASE_URL is required");
}

const MIGRATION_DIRS = [{ service: "cosa", dir: join(__dirname, "../migrations") }];

function sortByNumericPrefix(files) {
  return [...files].sort((a, b) => {
    const na = parseInt(a, 10);
    const nb = parseInt(b, 10);
    return na - nb;
  });
}

const BASELINE_MODE = process.argv.includes("--baseline");
const CHECK_MODE = process.argv.includes("--check");
const DOWN_FLAG_INDEX = process.argv.indexOf("--down");
const DOWN_MODE = DOWN_FLAG_INDEX !== -1;
const DOWN_STEPS = DOWN_MODE ? parseInt(process.argv[DOWN_FLAG_INDEX + 1] || "1", 10) || 1 : 0;

async function checkMigrationChecksums(client, MIGRATION_DIRS) {
  // Verify that all applied migrations have matching checksums. Returns array of errors (empty if OK).
  // This is used by --check mode for deploy-preflight to catch drift before applying anything.
  const errors = [];

  for (const { service, dir } of MIGRATION_DIRS) {
    const files = sortByNumericPrefix(readdirSync(dir).filter((f) => f.endsWith(".up.sql")));

    for (const file of files) {
      const sql = readFileSync(join(dir, file), "utf-8");
      const checksum = createHash("sha256").update(sql).digest("hex");

      const { rows } = await client.query(
        "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
        [service, file]
      );

      if (rows.length > 0) {
        const existing = rows[0].sha256;
        if (existing && existing !== checksum) {
          errors.push(
            `❌ migration ${service}/${file} was already applied with a different checksum — ` +
              `historical migrations are immutable, create a new migration instead of editing this one.`
          );
        }
      }
    }
  }

  return errors;
}

async function rollbackMigrations(client, MIGRATION_DIRS, steps) {
  let rolledBackCount = 0;
  const { rows } = await client.query(
    "SELECT service, filename FROM public.schema_migrations WHERE service = 'cosa' ORDER BY filename DESC"
  );

  const appliedSorted = sortByNumericPrefix(rows.map((r) => r.filename)).reverse().slice(0, steps);

  if (appliedSorted.length === 0) {
    console.log("[migrate:cosa] No migrations to roll back.");
    return;
  }

  const { dir } = MIGRATION_DIRS[0];

  for (const filename of appliedSorted) {
    const stem = filename.replace(/\.up\.sql$/, "");
    const downFile = `${stem}.down.sql`;
    const downPath = join(dir, downFile);

    if (!readdirSync(dir).includes(downFile)) {
      throw new Error(`Cannot roll back ${filename}: missing down migration ${downFile}`);
    }

    const downSql = readFileSync(downPath, "utf-8");
    console.log(`[migrate:cosa] rolling back cosa/${filename} using ${downFile}`);

    await client.query("BEGIN");
    try {
      await client.query(downSql);
      await client.query(
        "DELETE FROM public.schema_migrations WHERE service = 'cosa' AND filename = $1",
        [filename]
      );
      await client.query("COMMIT");
      rolledBackCount += 1;
    } catch (err) {
      await client.query("ROLLBACK");
      throw new Error(`failed to roll back cosa/${filename}: ${err instanceof Error ? err.message : err}`);
    }
  }

  console.log(`[migrate:cosa] rolled back ${rolledBackCount} migration(s)`);
}

async function main() {
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();

  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS public.schema_migrations (
        service TEXT NOT NULL,
        filename TEXT NOT NULL,
        sha256 TEXT,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (service, filename)
      );
    `);
    await client.query(`ALTER TABLE public.schema_migrations ADD COLUMN IF NOT EXISTS sha256 TEXT;`);

    // Rollback mode
    if (DOWN_MODE) {
      await rollbackMigrations(client, MIGRATION_DIRS, DOWN_STEPS);
      return;
    }

    // Checksum verification mode: check for drift without applying anything
    if (CHECK_MODE) {
      const errors = await checkMigrationChecksums(client, MIGRATION_DIRS);
      if (errors.length > 0) {
        console.error("[migrate:cosa] ❌ Checksum verification failed:");
        errors.forEach((err) => console.error(err));
        process.exit(1);
      }
      console.log("[migrate:cosa] ✓ All migration checksums valid (no drift detected)");
      return;
    }

    let appliedCount = 0;

    for (const { service, dir } of MIGRATION_DIRS) {
      const files = sortByNumericPrefix(readdirSync(dir).filter((f) => f.endsWith(".up.sql")));

      for (const file of files) {
        const sql = readFileSync(join(dir, file), "utf-8");
        const checksum = createHash("sha256").update(sql).digest("hex");

        const { rows } = await client.query(
          "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
          [service, file]
        );

        if (rows.length > 0) {
          const existing = rows[0].sha256;
          if (existing && existing !== checksum) {
            throw new Error(
              `migration ${service}/${file} was already applied with a different checksum — ` +
                `historical migrations are immutable, create a new migration instead of editing this one.`
            );
          }
          if (!existing) {
            // Backfill: migration đã applied từ trước khi bật checksum — coi nội dung hiện tại là đúng.
            await client.query(
              "UPDATE public.schema_migrations SET sha256 = $1 WHERE service = $2 AND filename = $3",
              [checksum, service, file]
            );
          }
          continue;
        }

        if (BASELINE_MODE) {
          // Database này đã có sẵn schema từ trước (migrate bằng cơ chế cũ,
          // ví dụ encore.dev/storage/sqldb's SQLDatabase). --baseline chỉ đánh
          // dấu "đã áp dụng" trong bảng theo dõi mới, KHÔNG chạy lại SQL (chạy
          // lại sẽ lỗi "relation already exists"). Chỉ dùng 1 lần cho database
          // đã tồn tại schema đúng — không dùng cho database rỗng.
          console.log(`[migrate:cosa] baselining ${service}/${file} (not executed)`);
          await client.query(
            "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
            [service, file, checksum]
          );
          appliedCount += 1;
          continue;
        }

        console.log(`[migrate:cosa] applying ${service}/${file}`);

        await client.query("BEGIN");
        try {
          await client.query(sql);
          await client.query(
            "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
            [service, file, checksum]
          );
          await client.query("COMMIT");
          appliedCount += 1;
        } catch (err) {
          await client.query("ROLLBACK");
          throw new Error(`failed to apply ${service}/${file}: ${err instanceof Error ? err.message : err}`);
        }
      }
    }

    console.log(
      appliedCount > 0
        ? `[migrate:cosa] ${BASELINE_MODE ? "baselined" : "applied"} ${appliedCount} migration(s)`
        : "[migrate:cosa] nothing to apply, already up to date"
    );
  } finally {
    await client.end();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
