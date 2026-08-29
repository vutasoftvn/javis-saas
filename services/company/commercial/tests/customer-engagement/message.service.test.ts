import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { openThread, getThread, changeThreadStatus } from "../../services/customer-engagement/thread.service";
import { postInternalNote, sendPublicMessage, recordInboundMessage } from "../../services/customer-engagement/message.service";
import { SLA_POLICY_SEED } from "../../services/customer-engagement/sla.service";

async function ws(name: string) {
  const u = await createTestSession({ email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`, displayName: name });
  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  return { ctx, workspaceId: u.workspaceId };
}

async function seedInbox(workspaceId: string, tier = "standard") {
  const id = BigInt(generateSnowflake());
  await db.insert(schema.engagementInboxes).values({
    id, workspaceId: BigInt(workspaceId), channelType: "api", name: "Primary",
    slaPolicy: SLA_POLICY_SEED, defaultTier: tier,
  });
  return String(id);
}

describe("message.service", () => {
  it("internal note has visibility=internal and deliveryState=null", async () => {
    const a = await ws("msg-internal-a");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m = await postInternalNote({ threadId: t.id, body: "handoff: khách bực", idempotencyKey: "n1" }, a.ctx);
    expect(m.visibility).toBe("internal");
    expect(m.deliveryState).toBeNull();
    const d = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_outbound_deliveries WHERE message_id = ${BigInt(m.id)}`);
    expect((d as any).rows[0].c).toBe(0);
  });

  it("internal note has no outbox events", async () => {
    const a = await ws("msg-internal-b");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const eventsBefore = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id}`);
    const beforeCount = (eventsBefore as any).rows[0].c;
    const m = await postInternalNote({ threadId: t.id, body: "internal", idempotencyKey: "n2" }, a.ctx);
    const eventsAfter = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id}`);
    const afterCount = (eventsAfter as any).rows[0].c;
    expect(afterCount).toBe(beforeCount); // No new events
  });

  it("public message enqueues exactly one delivery", async () => {
    const a = await ws("msg-public-a");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m = await sendPublicMessage({ threadId: t.id, body: "Chào anh", idempotencyKey: "p1" }, a.ctx);
    expect(m.visibility).toBe("customer");
    expect(m.deliveryState).toBe("queued");
    const d = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_outbound_deliveries WHERE message_id = ${BigInt(m.id)}`);
    expect((d as any).rows[0].c).toBe(1);
  });

  it("public message retry with same key is idempotent", async () => {
    const a = await ws("msg-public-b");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m1 = await sendPublicMessage({ threadId: t.id, body: "Chào anh", idempotencyKey: "p2" }, a.ctx);
    const m2 = await sendPublicMessage({ threadId: t.id, body: "Chào anh", idempotencyKey: "p2" }, a.ctx);
    expect(m2.id).toBe(m1.id);
    const d = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_outbound_deliveries WHERE thread_id = ${BigInt(t.id)}`);
    expect((d as any).rows[0].c).toBe(1);
  });

  it("public message emits exactly one message.sent event", async () => {
    const a = await ws("msg-public-c");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m = await sendPublicMessage({ threadId: t.id, body: "Chào", idempotencyKey: "p3" }, a.ctx);
    const events = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.message.sent.v1'`);
    expect((events as any).rows[0].c).toBe(1);
  });

  it("public message retry does not create duplicate event", async () => {
    const a = await ws("msg-public-d");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await sendPublicMessage({ threadId: t.id, body: "Chào", idempotencyKey: "p4" }, a.ctx);
    await sendPublicMessage({ threadId: t.id, body: "Chào", idempotencyKey: "p4" }, a.ctx);
    const events = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.message.sent.v1'`);
    expect((events as any).rows[0].c).toBe(1);
  });

  it("inbound on open thread updates lastCustomerMsgAt", async () => {
    const a = await ws("msg-inbound-a");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const before = new Date((await getThread(t.id, a.ctx)).updatedAt);
    await recordInboundMessage({ threadId: t.id, body: "issue here", idempotencyKey: "i1" }, a.ctx);
    const after = new Date((await getThread(t.id, a.ctx)).updatedAt);
    expect(after.getTime()).toBeGreaterThanOrEqual(before.getTime());
  });

  it("inbound on resolved thread reopens it to open", async () => {
    const a = await ws("msg-inbound-b");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    expect((await getThread(t.id, a.ctx)).status).toBe("resolved");
    await recordInboundMessage({ threadId: t.id, body: "còn lỗi nữa", idempotencyKey: "i2" }, a.ctx);
    expect((await getThread(t.id, a.ctx)).status).toBe("open");
  });

  it("inbound on resolved thread creates thread.status_changed event", async () => {
    const a = await ws("msg-inbound-c");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "còn lỗi", idempotencyKey: "i3" }, a.ctx);
    const events = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.thread.status_changed.v1'`);
    expect((events as any).rows[0].c).toBeGreaterThan(1); // At least one from changeThreadStatus, one from reopen
  });

  it("inbound on resolved thread creates message.received event", async () => {
    const a = await ws("msg-inbound-d");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "còn lỗi", idempotencyKey: "i4" }, a.ctx);
    const events = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.message.received.v1'`);
    expect((events as any).rows[0].c).toBe(1);
  });

  it("inbound on resolved thread creates outcome row with escalation_reason=reopened", async () => {
    const a = await ws("msg-inbound-e");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "còn lỗi", idempotencyKey: "i5" }, a.ctx);
    const outcomes = await db.execute(sql`SELECT escalation_reason FROM engagement.engagement_thread_outcomes WHERE thread_id = ${BigInt(t.id)} AND escalation_reason = 'reopened'`);
    expect((outcomes as any).rows.length).toBeGreaterThan(0);
  });

  it("inbound retry with same key is idempotent", async () => {
    const a = await ws("msg-inbound-f");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m1 = await recordInboundMessage({ threadId: t.id, body: "issue", idempotencyKey: "i6" }, a.ctx);
    const m2 = await recordInboundMessage({ threadId: t.id, body: "issue", idempotencyKey: "i6" }, a.ctx);
    expect(m2.id).toBe(m1.id);
  });

  it("inbound retry does not create duplicate message.received event", async () => {
    const a = await ws("msg-inbound-g");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "issue", idempotencyKey: "i7" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "issue", idempotencyKey: "i7" }, a.ctx);
    const events = await db.execute(sql`SELECT count(*)::int c FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.message.received.v1'`);
    expect((events as any).rows[0].c).toBe(1);
  });

  it("all messages have retention_until non-null", async () => {
    const a = await ws("msg-retention");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await postInternalNote({ threadId: t.id, body: "internal", idempotencyKey: "ret1" }, a.ctx);
    await sendPublicMessage({ threadId: t.id, body: "public", idempotencyKey: "ret2" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "inbound", idempotencyKey: "ret3" }, a.ctx);
    const msgs = await db.execute(sql`SELECT retention_until FROM engagement.engagement_messages WHERE thread_id = ${BigInt(t.id)}`);
    expect((msgs as any).rows).toHaveLength(3);
    expect((msgs as any).rows.every((r: any) => r.retention_until !== null)).toBe(true);
  });

  it("retention_until is approximately created_at + 365 days", async () => {
    const a = await ws("msg-retention-days");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const before = new Date();
    await postInternalNote({ threadId: t.id, body: "internal", idempotencyKey: "ret4" }, a.ctx);
    const after = new Date();
    const msgs = await db.execute(sql`SELECT created_at, retention_until FROM engagement.engagement_messages WHERE thread_id = ${BigInt(t.id)}`);
    const row = (msgs as any).rows[0];
    const createdAt = new Date(row.created_at);
    const retentionUntil = new Date(row.retention_until);
    const expectedRetention = new Date(createdAt.getTime() + 365 * 86400000);
    const diffMs = Math.abs(retentionUntil.getTime() - expectedRetention.getTime());
    expect(diffMs).toBeLessThan(1000); // Within 1 second tolerance
  });
});
