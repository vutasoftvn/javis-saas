import pg from "pg";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";

const pools: Map<string, pg.Pool> = new Map();

export function getOrCreatePool(connectionString: string): pg.Pool {
  let pool = pools.get(connectionString);
  if (!pool) {
    pool = new pg.Pool({ connectionString });
    pools.set(connectionString, pool);
  }
  return pool;
}

export function createDrizzleClient<T extends Record<string, unknown>>(
  connectionString: string,
  schema?: T
): NodePgDatabase<T> {
  const pool = getOrCreatePool(connectionString);
  return drizzle(pool, { schema }) as NodePgDatabase<T>;
}
