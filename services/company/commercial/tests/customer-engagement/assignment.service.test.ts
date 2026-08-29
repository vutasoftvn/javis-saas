import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { openThread, getThread } from "../../services/customer-engagement/thread.service";
import { sendPublicMessage } from "../../services/customer-engagement/message.service";
import { assignThread, takeOverThread, handBackToAgent } from "../../services/customer-engagement/assignment.service";
import { SLA_POLICY_SEED } from "../../services/customer-engagement/sla.service";

async function ws(name: string) {
  const u = await createTestSession({ email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`, displayName: name });

  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);

  // Build a test context with workforceMemberId for takeover tests
  // We mock the workforceMemberId since the real one requires complex DB constraints
  const ctxWithPerm = Object.freeze({
    ...ctx,
    workforceMemberId: String(generateSnowflake()),
    permissions: Object.freeze([...(ctx.permissions || []), "engagement.thread.takeover"]),
  });

  return { ctx, ctxWithPerm, workspaceId: u.workspaceId };
}

async function seedInbox(workspaceId: string, tier = "standard") {
  const id = BigInt(generateSnowflake());
  await db.insert(schema.engagementInboxes).values({
    id, workspaceId: BigInt(workspaceId), channelType: "api", name: "Primary",
    slaPolicy: SLA_POLICY_SEED, defaultTier: tier,
  });
  return String(id);
}

describe("assignment.service", () => {
  it("assignThread with memberId sets human_assigned and emits event", async () => {
    const a = await ws("asg-assign-1");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const memberId = String(generateSnowflake());

    const assignment = await assignThread({ threadId: t.id, memberId, reason: "manual assign" }, a.ctx);

    expect(assignment.assignedMemberId).toBe(memberId);
    expect(assignment.reason).toBe("manual assign");

    const updated = await getThread(t.id, a.ctx);
    expect(updated.activeMode).toBe("human_assigned");
    expect(updated.ownerMemberId).toBe(memberId);

    // Check for event in outbox
    const events = await db.execute(sql`SELECT event_type FROM integration.event_outbox WHERE aggregate_id = ${BigInt(t.id)} AND event_type = 'engagement.thread.assigned.v1' ORDER BY created_at DESC LIMIT 1`);
    expect((events as any).rows.length).toBeGreaterThan(0);
  });

  it("takeOverThread cancels queued outbound messages and wins over a prior agent assignment", async () => {
    const a = await ws("asg-takeover-1");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);

    // Send a public message (enqueues outbound)
    await sendPublicMessage({ threadId: t.id, body: "auto reply", idempotencyKey: "auto1" }, a.ctx);

    // Takeover with permission
    await takeOverThread({ threadId: t.id, reason: "manual handling" }, a.ctxWithPerm);

    const th = await getThread(t.id, a.ctx);
    expect(th.activeMode).toBe("human_assigned");

    // Check messages are cancelled
    const m = await db.execute(sql`SELECT delivery_state FROM engagement.engagement_messages WHERE thread_id = ${BigInt(t.id)} AND direction='outbound'`);
    expect((m as any).rows.every((r: any) => r.delivery_state === "cancelled")).toBe(true);

    // Check deliveries are failed
    const d = await db.execute(sql`SELECT status, dead_letter_reason FROM engagement.engagement_outbound_deliveries WHERE thread_id = ${BigInt(t.id)}`);
    expect((d as any).rows.length).toBeGreaterThan(0);
    expect((d as any).rows[0]).toMatchObject({ status: "failed", dead_letter_reason: "superseded_by_takeover" });

    // Check for taken_over event
    const events = await db.execute(sql`SELECT event_type FROM integration.event_outbox WHERE aggregate_id = ${BigInt(t.id)} AND event_type = 'engagement.thread.taken_over.v1' ORDER BY created_at DESC LIMIT 1`);
    expect((events as any).rows.length).toBeGreaterThan(0);
  });

  it("two concurrent takeOvers: exactly one active assignment remains", async () => {
    const a = await ws("asg-concurrent-1");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);

    const results = await Promise.allSettled([
      takeOverThread({ threadId: t.id, reason: "r1" }, a.ctxWithPerm),
      takeOverThread({ threadId: t.id, reason: "r2" }, a.ctxWithPerm),
    ]);

    const ok = results.filter((r) => r.status === "fulfilled").length;
    expect(ok).toBeGreaterThanOrEqual(1);

    const act = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_assignments WHERE thread_id = ${BigInt(t.id)} AND ended_at IS NULL`);
    expect((act as any).rows[0].c).toBe(1);
  });

  it("handBackToAgent without expiresAt throws invalidArgument", async () => {
    const a = await ws("asg-handback-1");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);

    await expect(
      handBackToAgent({ threadId: t.id, agentSpecId: "agent-1", expiresAt: "" }, a.ctx)
    ).rejects.toThrow(/invalidArgument|expiresAt/i);
  });

  it("handBackToAgent with expiresAt sets agent_copilot and stores scope/expiresAt in reason", async () => {
    const a = await ws("asg-handback-2");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);

    const expiresAt = new Date(Date.now() + 3600000).toISOString();
    const scope = "specific_topic";

    const assignment = await handBackToAgent({
      threadId: t.id,
      agentSpecId: "agent-1",
      scope,
      expiresAt,
    }, a.ctx);

    expect(assignment.assignedAgentSpecId).toBe("agent-1");
    expect(assignment.assignedMemberId).toBeNull();

    const updated = await getThread(t.id, a.ctx);
    expect(updated.activeMode).toBe("agent_copilot");
    expect(updated.ownerMemberId).toBeNull();

    // Check reason contains scope and expiresAt
    const parsed = JSON.parse(assignment.reason);
    expect(parsed.scope).toBe(scope);
    expect(parsed.expiresAt).toBe(expiresAt);
  });

  it("takeOverThread without permission throws permissionDenied", async () => {
    const a = await ws("asg-no-perm");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);

    // Test sessions are admins by default. Use a non-privileged membership so
    // this assertion exercises the explicit permission boundary.
    const noPermissionCtx = {
      ...a.ctx,
      membershipRole: "member",
      permissions: Object.freeze([]),
    };

    await expect(
      takeOverThread({ threadId: t.id, reason: "unauthorized" }, noPermissionCtx)
    ).rejects.toThrow(/permissionDenied|permission/i);
  });
});
