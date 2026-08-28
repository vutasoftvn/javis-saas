import pg from "pg";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";
import { isStagingOrProd } from "../shared/env";

const pools: Map<string, pg.Pool> = new Map();

export function resolveCosaDatabaseUrl(): string {
  const url = process.env.COSA_DATABASE_URL || process.env.CONTROL_PLANE_DATABASE_URL;
  if (!url) {
    if (isStagingOrProd()) {
      throw new Error(
        "COSA_DATABASE_URL (hoặc CONTROL_PLANE_DATABASE_URL) must be explicitly set in staging/production"
      );
    }
    throw new Error(
      "COSA_DATABASE_URL (hoặc CONTROL_PLANE_DATABASE_URL) is required; set it in .env for local dev"
    );
  }
  return url;
}

export const DEFAULT_COSA_DB_URL = "";

export function getOrCreatePool(connectionString: string = DEFAULT_COSA_DB_URL): pg.Pool {
  const targetUri = connectionString || resolveCosaDatabaseUrl();
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
  const conn = connectionString || resolveCosaDatabaseUrl();
  const pool = getOrCreatePool(conn);
  return drizzle(pool, { schema }) as NodePgDatabase<T>;
}

