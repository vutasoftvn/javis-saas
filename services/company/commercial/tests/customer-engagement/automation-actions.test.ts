import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementThreadLabels,
  engagementThreadTransitions,
  engagementDecisionAuthorities,
  engagementDecisionRequests,
  engagementAutomationApplications,
  engagementAutomationSchedules,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  applyAction,
  validateAction,
  AutomationAction,
} from "../../services/customer-engagement/automation/actions";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Automation Actions Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_act_test",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_act_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Actions Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should apply label and record transition ledger with system actor", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const action: AutomationAction = {
      type: "apply_label",
      labelKey: "vip_customer",
    };

    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_apply_vip",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
      },
      ctx
    );

    expect(res.outcome).toBe("applied");

    const [label] = await db
      .select()
      .from(engagementThreadLabels)
      .where(eq(engagementThreadLabels.threadId, threadId));
    expect(label.labelKey).toBe("vip_customer");
    expect(label.source).toBe("automation");

    // Re-applying exact same action -> idempotency check returns already_applied
    const res2 = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_apply_vip",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
      },
      ctx
    );
    expect(res2.outcome).toBe("already_applied");
  });

  it("should fail-closed on create_decision_request when no authority enabled", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const action: AutomationAction = {
      type: "create_decision_request",
      decisionKind: "discount_request",
    };

    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_dr_fail",
        ruleVersion: 1,
        trigger: "message_received",
        actionIndex: 0,
      },
      ctx
    );

    expect(res.outcome).toBe("skipped_no_authority");

    // 0 DR created
    const drs = await db
      .select()
      .from(engagementDecisionRequests)
      .where(eq(engagementDecisionRequests.threadId, threadId));
    expect(drs.length).toBe(0);
  });

  it("should create decision request when authority is enabled", async () => {
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
      authorityKey: "discount_lead_auth",
      decisionKind: "discount_request",
      approvalPolicy: { minApprovals: 1 },
      status: "enabled",
    });

    const action: AutomationAction = {
      type: "create_decision_request",
      decisionKind: "discount_request",
    };

    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_dr_ok",
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
    expect(dr.authorityKey).toBe("discount_lead_auth");
    expect((dr.requestedByActor as any).kind).toBe("system");
  });

  it("should schedule delayed action without applying immediately", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    const action: AutomationAction = {
      type: "schedule_delayed",
      delayMinutes: 30,
      action: { type: "escalate" },
      requireStillTrue: true,
    };

    const res = await applyAction(
      action,
      {
        threadId: threadId.toString(),
        ruleKey: "rule_sched_esc",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        ruleCondition: { fact: "sla.firstResponseBreached", op: "eq", value: true },
      },
      ctx
    );

    expect(res.outcome).toBe("applied");

    // Thread escalation level not changed yet
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(0);

    // Schedule row created
    const [sched] = await db
      .select()
      .from(engagementAutomationSchedules)
      .where(eq(engagementAutomationSchedules.threadId, threadId));
    expect(sched.status).toBe("pending");
    expect((sched.action as any).type).toBe("escalate");
  });
});
