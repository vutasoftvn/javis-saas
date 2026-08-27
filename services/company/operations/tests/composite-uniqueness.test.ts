import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../identity/models/db";

describe("workspace composite uniqueness", () => {
  it("every link target has UNIQUE (id, workspace_id)", async () => {
    const rows = await db.execute(sql`
      SELECT conrelid::regclass::text AS tbl
      FROM pg_constraint
      WHERE contype = 'u'
        AND conrelid::regclass::text IN (
          'strategy.projects','strategy.portfolios',
          'strategy.okr_objectives','operating.tasks')
        AND pg_get_constraintdef(oid) LIKE '%(id, workspace_id)%'
    `);
    const tables = (rows as unknown as { rows: { tbl: string }[] }).rows.map((r) => r.tbl);
    expect(new Set(tables)).toEqual(
      new Set(["strategy.projects", "strategy.portfolios", "strategy.okr_objectives", "operating.tasks"])
    );
  });
});
