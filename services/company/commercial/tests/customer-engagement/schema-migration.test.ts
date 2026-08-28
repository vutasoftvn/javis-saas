import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../db";

describe("engagement schema migration", () => {
  it("creates the engagement schema and core tables", async () => {
    const rows = await db.execute(sql`
      SELECT table_name FROM information_schema.tables
      WHERE table_schema = 'engagement' ORDER BY table_name;
    `);
    const names = (rows as any).rows.map((r: any) => r.table_name);
    for (const t of [
      "engagement_inboxes", "engagement_channel_endpoints", "engagement_threads",
      "engagement_messages", "engagement_message_attachments", "engagement_assignments",
      "engagement_thread_labels", "engagement_thread_outcomes", "engagement_customer_interactions",
      "engagement_thread_transitions", "engagement_decision_authorities",
      "engagement_decision_authority_grants", "engagement_decision_requests",
      "engagement_decision_request_approvals", "engagement_decision_request_events",
      "engagement_escalation_routes", "engagement_legal_holds", "engagement_data_subject_requests",
      "engagement_outbound_deliveries", "engagement_identity_review_items",
    ]) {
      expect(names).toContain(t);
    }
  });

  it("retention_until is NOT NULL on messages / attachments / interactions (fail-closed)", async () => {
    const rows = await db.execute(sql`
      SELECT table_name, is_nullable FROM information_schema.columns
      WHERE table_schema = 'engagement' AND column_name = 'retention_until';
    `);
    for (const r of (rows as any).rows) expect(r.is_nullable).toBe("NO");
  });

  it("enforces unique (thread_id, idempotency_key) on engagement_messages", async () => {
    const rows = await db.execute(sql`
      SELECT indexdef FROM pg_indexes
      WHERE schemaname = 'engagement' AND tablename = 'engagement_messages';
    `);
    const defs = (rows as any).rows.map((r: any) => r.indexdef).join("\n");
    expect(defs).toMatch(/UNIQUE.*\(thread_id, idempotency_key\)/i);
  });

  it("enforces composite FK on message child tables", async () => {
    const rows = await db.execute(sql`
      SELECT table_name FROM information_schema.table_constraints
      WHERE table_schema = 'engagement'
        AND table_name IN ('engagement_message_attachments','engagement_outbound_deliveries')
        AND constraint_type = 'FOREIGN KEY';
    `);
    const t = (rows as any).rows.map((r: any) => r.table_name);
    expect(t).toContain('engagement_message_attachments');
    expect(t).toContain('engagement_outbound_deliveries');
  });
});
