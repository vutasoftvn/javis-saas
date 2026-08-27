import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";

async function fkCount(table: string) {
  const r = await db.execute(sql`
    SELECT count(*)::int AS n FROM pg_constraint
    WHERE conrelid = ${table}::regclass AND contype = 'f'`);
  return (r as any).rows[0].n as number;
}

describe("project link tables", () => {
  it("task_projects has both composite FKs", async () => {
    expect(await fkCount("operating.task_projects")).toBe(2);
  });
  it("okr_objective_projects has both composite FKs", async () => {
    expect(await fkCount("strategy.okr_objective_projects")).toBe(2);
  });
});
