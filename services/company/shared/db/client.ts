import pg from "pg";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";
import { isStagingOrProd } from "../env";

const pools: Map<string, pg.Pool> = new Map();

export function resolveCompanyDatabaseUrl(): string {
  const url = process.env.COMPANY_DATABASE_URL || process.env.DATABASE_URL;
  if (!url) {
    if (isStagingOrProd()) {
      throw new Error(
        "COMPANY_DATABASE_URL (hoặc DATABASE_URL) must be explicitly set in staging/production"
      );
    }
    throw new Error(
      "COMPANY_DATABASE_URL (hoặc DATABASE_URL) is required; set it in .env for local dev"
    );
  }
  return url;
}

export const DEFAULT_COMPANY_DB_URL = "";

export function getOrCreatePool(connectionString: string = DEFAULT_COMPANY_DB_URL): pg.Pool {
  const targetUri = connectionString || resolveCompanyDatabaseUrl();
  let pool = pools.get(targetUri);
  if (!pool) {
    pool = new pg.Pool({ connectionString: targetUri });
    pools.set(targetUri, pool);
  }
  return pool;
}

export function createDrizzleClient<T extends Record<string, unknown>>(
  connectionString: string = DEFAULT_COMPANY_DB_URL,
  schema?: T
): NodePgDatabase<T> {
  const conn = connectionString || resolveCompanyDatabaseUrl();
  const pool = getOrCreatePool(conn);
  return drizzle(pool, { schema }) as NodePgDatabase<T>;
}

