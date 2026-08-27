import pg from "pg";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";
import { isStagingOrProd } from "../shared/env";

const pools: Map<string, pg.Pool> = new Map();

const DEV_COSA_DB_URL =
  "postgresql://cosa_central_admin:SecureCentralPass2026@127.0.0.1:5434/cosa?sslmode=disable";

function resolveCosaDatabaseUrl(): string {
  const url = process.env.COSA_DATABASE_URL || process.env.CONTROL_PLANE_DATABASE_URL;
  if (isStagingOrProd()) {
    if (!url || url === DEV_COSA_DB_URL) {
      throw new Error(
        "COSA_DATABASE_URL (hoặc CONTROL_PLANE_DATABASE_URL) must be explicitly set in staging/production, cannot use default DSN"
      );
    }
  }
  return url || DEV_COSA_DB_URL;
}

export const DEFAULT_COSA_DB_URL = resolveCosaDatabaseUrl();

export function getOrCreatePool(connectionString: string = DEFAULT_COSA_DB_URL): pg.Pool {
  const targetUri = connectionString || DEFAULT_COSA_DB_URL;
  let pool = pools.get(targetUri);
  if (!pool) {
    pool = new pg.Pool({ connectionString: targetUri });
    pools.set(targetUri, pool);
  }
  return pool;
}

export function createDrizzleClient<T extends Record<string, unknown>>(
  connectionString: string = DEFAULT_COSA_DB_URL,
  schema?: T
): NodePgDatabase<T> {
  const conn = connectionString || DEFAULT_COSA_DB_URL;
  const pool = getOrCreatePool(conn);
  return drizzle(pool, { schema }) as NodePgDatabase<T>;
}
