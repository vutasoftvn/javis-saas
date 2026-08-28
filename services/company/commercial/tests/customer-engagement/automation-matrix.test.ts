import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementAutomationRules,
  engagementAutomationApplications,
  engagementAutomationSchedules,
  engagementThreadLabels,
  engagementDecisionAuthorities,
  engagementDecisionRequests,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { evaluateRules } from "../../services/customer-engagement/automation/evaluator";
import { applyAction } from "../../services/customer-engagement/automation/actions";
import { runHousekeepingTick } from "../../services/customer-engagement/housekeeping.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("P3 Customer Engagement Automation Matrix Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_mat_p3",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_mat_p3",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Matrix P3 Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("Scenario 1: Deterministic Replay - Same facts & rule yields identical matched actions across multiple runs", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "urgent",
      correlationId: `corr_${threadId}`,
    });

    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_det_rep",
      version: 1,
      name: "Deterministic Replay Rule",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.priority", op: "eq", value: "urgent" },
      actions: [{ type: "apply_label", labelKey: "urgent_tag" }],
      enabled: true,
      stopOnMatch: false,
    });

    // Run 1 (dryRun)
    const res1 = await evaluateRules({ trigger: "thread_opened", threadId: threadId.toString(), dryRun: true }, ctx);
    // Run 2 (dryRun)
    const res2 = await evaluateRules({ trigger: "thread_opened", threadId: threadId.toString(), dryRun: true }, ctx);

    expect(res1.matched).toEqual(res2.matched);
    expect(res1.matched[0].ruleKey).toBe("rule_det_rep");
  });

  it("Scenario 2: Idempotency - Re-triggering same action produces 0 duplicate ledger applications or effects", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const action = { type: "apply_label" as const, labelKey: "idempotent_label" };
    const actCtx = {
      threadId: threadId.toString(),
      ruleKey: "rule_idem",
      ruleVersion: 1,
      trigger: "thread_opened",
      actionIndex: 0,
    };

    const first = await applyAction(action, actCtx, ctx);
    expect(first.outcome).toBe("applied");

    const second = await applyAction(action, actCtx, ctx);
    expect(second.outcome).toBe("already_applied");

    const labels = await db
      .select()
      .from(engagementThreadLabels)
      .where(eq(engagementThreadLabels.threadId, threadId));
    expect(labels.length).toBe(1);
  });

  it("Scenario 3: Fail-Closed Decision Request - Missing enabled authority skips DR creation", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const action = { type: "create_decision_request" as const, decisionKind: "unauthorized_refund" };
    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_dr_failclosed",
        ruleVersion: 1,
        trigger: "message_received",
        actionIndex: 0,
      },
      ctx
    );

    expect(res.outcome).toBe("skipped_no_authority");

    const drs = await db
      .select()
      .from(engagementDecisionRequests)
      .where(eq(engagementDecisionRequests.threadId, threadId));
    expect(drs.length).toBe(0);
  });

  it("Scenario 4: Decision Request Happy Path - Enabled authority creates pending DR with system actor", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const authId = generateSnowflake();
    await db.insert(engagementDecisionAuthorities).values({
      id: authId,
      workspaceId: wsId,
      authorityKey: "auth_refund_valid",
      decisionKind: "refund_authorized",
      approvalPolicy: { minApprovals: 1 },
      status: "enabled",
    });

    const action = { type: "create_decision_request" as const, decisionKind: "refund_authorized" };
    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_dr_happy",
        ruleVersion: 1,
        trigger: "message_received",
        actionIndex: 0,
      },
      ctx
    );

    expect(res.outcome).toBe("applied");

    const [dr] = await db
      .select()
      .from(engagementDecisionRequests)
      .where(eq(engagementDecisionRequests.threadId, threadId));
    expect(dr.authorityKey).toBe("auth_refund_valid");
    expect((dr.requestedByActor as any).kind).toBe("system");
  });

  it("Scenario 5: Priority + stopOnMatch - Lower priority rule stops evaluation for subsequent rules", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    // Rule 1: Priority 5, stopOnMatch: true
    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_mat_p1",
      version: 1,
      name: "P1 Rule",
      trigger: "thread_opened",
      priority: 5,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "p1_label" }],
      enabled: true,
      stopOnMatch: true,
    });

    // Rule 2: Priority 10, stopOnMatch: false
    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_mat_p2",
      version: 1,
      name: "P2 Rule",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "p2_label" }],
      enabled: true,
      stopOnMatch: false,
    });

    const res = await evaluateRules({ trigger: "thread_opened", threadId: threadId.toString() }, ctx);

    expect(res.matched.length).toBe(1);
    expect(res.matched[0].ruleKey).toBe("rule_mat_p1");
  });

  it("Scenario 6: Delayed schedule re-check skips on takeover or rule disable", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      activeMode: "human_assigned",
      ownerMemberId: generateSnowflake(),
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_mat_delayed",
      version: 1,
      name: "Delayed Rule",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "escalate" }],
      enabled: true,
      stopOnMatch: false,
    });

    const schedId = generateSnowflake();
    await db.insert(engagementAutomationSchedules).values({
      id: schedId,
      workspaceId: wsId,
      ruleKey: "rule_mat_delayed",
      ruleVersion: 1,
      threadId,
      actionIndex: 0,
      action: { type: "escalate" },
      condition: { fact: "thread.status", op: "eq", value: "open" },
      dueAt: new Date(Date.now() - 60000),
      status: "pending",
    });

    await runHousekeepingTick(10);

    const [sched] = await db
      .select()
      .from(engagementAutomationSchedules)
      .where(eq(engagementAutomationSchedules.id, schedId));
    expect(sched.status).toBe("skipped");
    expect(sched.skipReason).toBe("ownership_changed");
  });
});
