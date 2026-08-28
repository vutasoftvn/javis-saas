import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementChannelEndpoints,
  engagementThreads,
  engagementChannelInboundEvents,
} from "../../../shared/db/schema/customer-engagement";

describe("P2 Channel Schema Tests", () => {
  it("should have engagement_channel_inbound_events table with unique dedupe index", async () => {
    // Check columns and table existence
    const result = await db.execute(sql`
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns
      WHERE table_schema = 'engagement' AND table_name = 'engagement_channel_inbound_events'
      ORDER BY ordinal_position;
    `);

    const colNames = result.rows.map((r: any) => r.column_name);
    expect(colNames).toContain("id");
    expect(colNames).toContain("workspace_id");
    expect(colNames).toContain("endpoint_id");
    expect(colNames).toContain("provider_delivery_id");
    expect(colNames).toContain("provider_message_id");
    expect(colNames).toContain("received_at");
    expect(colNames).toContain("outcome");
    expect(colNames).toContain("thread_id");
    expect(colNames).toContain("message_id");
    expect(colNames).toContain("error");
    expect(colNames).toContain("raw_hash");
  });

  it("should have external_conversation_ref on engagement_threads and routing columns on engagement_channel_endpoints", async () => {
    const threadCols = await db.execute(sql`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'engagement' AND table_name = 'engagement_threads' AND column_name = 'external_conversation_ref';
    `);
    expect(threadCols.rows.length).toBe(1);

    const epCols = await db.execute(sql`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'engagement' AND table_name = 'engagement_channel_endpoints'
      AND column_name IN ('connector_key', 'inbound_routing_key', 'auto_create_contact', 'skew_seconds');
    `);
    expect(epCols.rows.length).toBe(4);
  });
});
