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
import { Client } from "pg";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const DATABASE_URL =
  process.env.COSA_DATABASE_URL ||
  process.env.CONTROL_PLANE_DATABASE_URL ||
  "postgresql://cosa_central_admin:SecureCentralPass2026@127.0.0.1:5434/cosa?sslmode=disable";

const MIGRATION_DIRS = [{ service: "cosa", dir: join(__dirname, "../migrations") }];

function sortByNumericPrefix(files) {
  return [...files].sort((a, b) => {
    const na = parseInt(a, 10);
    const nb = parseInt(b, 10);
    return na - nb;
  });
}

const BASELINE_MODE = process.argv.includes("--baseline");

async function main() {
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();

  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS public.schema_migrations (
        service TEXT NOT NULL,
        filename TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (service, filename)
      );
    `);

    let appliedCount = 0;

    for (const { service, dir } of MIGRATION_DIRS) {
      const files = sortByNumericPrefix(readdirSync(dir).filter((f) => f.endsWith(".up.sql")));

      for (const file of files) {
        const { rows } = await client.query(
          "SELECT 1 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
          [service, file]
        );
        if (rows.length > 0) continue;

        if (BASELINE_MODE) {
          // Database này đã có sẵn schema từ trước (migrate bằng cơ chế cũ,
          // ví dụ encore.dev/storage/sqldb's SQLDatabase). --baseline chỉ đánh
          // dấu "đã áp dụng" trong bảng theo dõi mới, KHÔNG chạy lại SQL (chạy
          // lại sẽ lỗi "relation already exists"). Chỉ dùng 1 lần cho database
          // đã tồn tại schema đúng — không dùng cho database rỗng.
          console.log(`[migrate:cosa] baselining ${service}/${file} (not executed)`);
          await client.query(
            "INSERT INTO public.schema_migrations (service, filename) VALUES ($1, $2)",
            [service, file]
          );
          appliedCount += 1;
          continue;
        }

        const sql = readFileSync(join(dir, file), "utf-8");
        console.log(`[migrate:cosa] applying ${service}/${file}`);

        await client.query("BEGIN");
        try {
          await client.query(sql);
          await client.query(
            "INSERT INTO public.schema_migrations (service, filename) VALUES ($1, $2)",
            [service, file]
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
