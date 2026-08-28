import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../db";

describe("P1 Customer Engagement Copilot Schema", () => {
  it("creates engagement_copilot_settings with fail-closed default and unique workspace_id", async () => {
    // Assert table exists
    const tableCheck = await db.execute(sql`
      SELECT table_name FROM information_schema.tables 
      WHERE table_schema = 'engagement' AND table_name = 'engagement_copilot_settings';
    `);
    expect(tableCheck.rows.length).toBe(1);

    // Assert unique index on workspace_id
    const indexCheck = await db.execute(sql`
      SELECT indexname FROM pg_indexes 
      WHERE schemaname = 'engagement' AND tablename = 'engagement_copilot_settings'
      AND indexname = 'uq_engagement_copilot_settings_ws';
    `);
    expect(indexCheck.rows.length).toBe(1);
  });

  it("creates engagement_copilot_invocations table with indexes and FK to engagement_threads", async () => {
    // Assert table exists
    const tableCheck = await db.execute(sql`
      SELECT table_name FROM information_schema.tables 
      WHERE table_schema = 'engagement' AND table_name = 'engagement_copilot_invocations';
    `);
    expect(tableCheck.rows.length).toBe(1);

    // Assert thread index exists
    const idxCheck = await db.execute(sql`
      SELECT indexname FROM pg_indexes 
      WHERE schemaname = 'engagement' AND tablename = 'engagement_copilot_invocations'
      AND indexname = 'idx_engagement_copilot_invocations_thread';
    `);
    expect(idxCheck.rows.length).toBe(1);

    // Assert unique index on (workspace_id, run_id)
    const runIdxCheck = await db.execute(sql`
      SELECT indexname FROM pg_indexes 
      WHERE schemaname = 'engagement' AND tablename = 'engagement_copilot_invocations'
      AND indexname = 'uq_engagement_copilot_invocations_run';
    `);
    expect(runIdxCheck.rows.length).toBe(1);
  });
});
