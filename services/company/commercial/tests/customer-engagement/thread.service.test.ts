import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { openThread, getThread, changeThreadStatus, listThreads } from "../../services/customer-engagement/thread.service";
import { SLA_POLICY_SEED } from "../../services/customer-engagement/sla.service";
import { setEscalationRoute } from "../../services/customer-engagement/escalation.service";

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

describe("thread.service", () => {
  it("openThread creates an open/team_queue thread scoped to workspace", async () => {
    const a = await ws("thr-a");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    expect(t.status).toBe("open");
    expect(t.activeMode).toBe("team_queue");
    expect(t.correlationId).toBeTruthy();
  });

  it("getThread from another workspace throws not found", async () => {
    const a = await ws("thr-a2"); const b = await ws("thr-b2");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await expect(getThread(t.id, b.ctx)).rejects.toThrow(/not found/i);
  });

  it("changeThreadStatus enforces the transition table and records a transition row", async () => {
    const a = await ws("thr-a3");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "pending_customer", reasonCode: "awaiting_reply" }, a.ctx);
    await expect(
      changeThreadStatus(t.id, { to: "resolved", reasonCode: "x" }, a.ctx)
    ).resolves.toMatchObject({ status: "resolved" });
    const rows = await db.execute(
      // @ts-ignore raw
      require("drizzle-orm").sql`SELECT current_state FROM engagement.engagement_thread_transitions WHERE thread_id = ${BigInt(t.id)} ORDER BY created_at`
    );
    expect((rows as any).rows.map((r: any) => r.current_state)).toEqual(["open", "pending_customer", "resolved"]);
  });

  it("openThread vip tier with no escalation route bound fails with failedPrecondition", async () => {
    const a = await ws("thr-vip-no-route");
    const inbox = await seedInbox(a.workspaceId, "vip");
    await expect(
      openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx)
    ).rejects.toThrow(/failed.?precondition|escalation|route/i);
  });

  it("openThread vip tier succeeds after setting escalation route, returns firstResponseDueAt", async () => {
    const a = await ws("thr-vip-with-route");
    const inbox = await seedInbox(a.workspaceId, "vip");
    const memberId = BigInt(generateSnowflake());
    await setEscalationRoute({
      workspaceId: a.workspaceId,
      routeKey: "support-oncall",
      role: "primary",
      workforceMemberId: String(memberId),
    }, a.ctx);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    expect(t.status).toBe("open");
    expect(t.tier).toBe("vip");
    expect(t.firstResponseDueAt).toBeTruthy(); // Must be non-null
  });

  it("openThread standard tier succeeds with no route bound, returns firstResponseDueAt", async () => {
    const a = await ws("thr-standard-no-route");
    const inbox = await seedInbox(a.workspaceId, "standard");
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    expect(t.status).toBe("open");
    expect(t.tier).toBe("standard");
    expect(t.firstResponseDueAt).toBeTruthy(); // Must be non-null
  });

  it("openThread emits engagement.thread.opened.v1 event to outbox", async () => {
    const a = await ws("thr-events-open");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const rows = await db.execute(
      // @ts-ignore raw
      sql`SELECT event_type, aggregate_id FROM integration.event_outbox WHERE aggregate_id = ${t.id} AND event_type = 'engagement.thread.opened.v1'`
    );
    expect((rows as any).rows).toHaveLength(1);
    expect((rows as any).rows[0].event_type).toBe("engagement.thread.opened.v1");
  });

  it("changeThreadStatus to resolved emits both status_changed and resolved events", async () => {
    const a = await ws("thr-events-resolved");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    const rows = await db.execute(
      // @ts-ignore raw
      sql`SELECT event_type FROM integration.event_outbox WHERE aggregate_id = ${t.id} ORDER BY created_at DESC`
    );
    const eventTypes = (rows as any).rows.map((r: any) => r.event_type);
    expect(eventTypes).toContain("engagement.thread.status_changed.v1");
    expect(eventTypes).toContain("engagement.thread.resolved.v1");
  });
});
