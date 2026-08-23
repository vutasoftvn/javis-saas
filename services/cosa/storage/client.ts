import pg from "pg";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";

const pools: Map<string, pg.Pool> = new Map();

export const DEFAULT_COSA_DB_URL =
  process.env.COSA_DATABASE_URL ||
  process.env.CONTROL_PLANE_DATABASE_URL ||
  "postgresql://cosa_central_admin:SecureCentralPass2026@127.0.0.1:5434/cosa?sslmode=disable";

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
