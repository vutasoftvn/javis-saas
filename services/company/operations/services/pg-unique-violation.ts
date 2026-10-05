// Typed detection of Postgres unique_violation (SQLSTATE 23505). Drizzle wraps
// driver errors ("Failed query: ...") and keeps the pg error in `cause`, so the
// code is searched along the cause chain (same walk as okr-db-errors.ts).

interface PgErrorLike {
  code?: unknown;
  constraint?: unknown;
  cause?: PgErrorLike | null;
}

const UNIQUE_VIOLATION = "23505";
const MAX_CAUSE_DEPTH = 4;

/**
 * True when `err` (or a nested `cause`) is a 23505. When `constraint` is given, the
 * violated constraint/index name must match too, so unrelated unique violations pass through.
 */
export function isUniqueViolation(err: unknown, constraint?: string): boolean {
  let cur: PgErrorLike | null | undefined = err as PgErrorLike | null | undefined;
  for (let depth = 0; cur && typeof cur === "object" && depth < MAX_CAUSE_DEPTH; depth++) {
    if (cur.code === UNIQUE_VIOLATION && (constraint === undefined || cur.constraint === constraint)) return true;
    cur = cur.cause;
  }
  return false;
}
