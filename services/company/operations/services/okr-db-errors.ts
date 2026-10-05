import { APIError } from "encore.dev/api";

interface PgErrorLike {
  code?: unknown;
  message?: unknown;
  cause?: PgErrorLike | null;
}

const CHECK_VIOLATION = "23514";

function findCheckViolation(err: unknown): PgErrorLike | null {
  let cur: PgErrorLike | null | undefined = err as PgErrorLike | null | undefined;
  for (let depth = 0; cur && typeof cur === "object" && depth < 4; depth++) {
    if (cur.code === CHECK_VIOLATION) return cur;
    cur = cur.cause;
  }
  return null;
}

/** Map Postgres 23514 (raised by OKR alignment triggers) to failedPrecondition; return anything else unchanged. */
export function mapOkrDbError(err: unknown): unknown {
  const hit = findCheckViolation(err);
  if (!hit) return err;
  return APIError.failedPrecondition(typeof hit.message === "string" ? hit.message : "okr alignment constraint violated");
}

export async function withOkrDbErrors<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    throw mapOkrDbError(err);
  }
}
