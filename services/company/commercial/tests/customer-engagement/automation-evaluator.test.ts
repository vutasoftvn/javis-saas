import { describe, expect, it, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementAutomationRules,
  engagementThreadLabels,
  engagementAssignments,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { evaluateRules } from "../../services/customer-engagement/automation/evaluator";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Automation Evaluator Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_eval_test",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_eval_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Evaluator Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should match rule on trigger, evaluate condition and apply actions in priority order", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "normal",
      correlationId: `corr_${threadId}`,
    });

    const msgId = generateSnowflake();
    await db.insert(engagementMessages).values({
      id: msgId,
      workspaceId: wsId,
      threadId,
      direction: "inbound",
      visibility: "customer",
      senderKind: "customer",
      body: "Tôi cần hỗ trợ",
      bodyContentHash: "hash_msg_eval",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_eval_${msgId}`,
    });

    // Rule 1: Priority 10 -> apply label
    const rule1Id = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: rule1Id,
      workspaceId: wsId,
      ruleKey: "rule_inbound_label",
      version: 1,
      name: "Inbound Label Rule",
      trigger: "message_received",
      priority: 10,
      condition: {
        all: [
          { fact: "lastMessage.direction", op: "eq", value: "inbound" },
          { fact: "thread.status", op: "eq", value: "open" },
        ],
      },
      actions: [{ type: "apply_label", labelKey: "auto_received" }],
      enabled: true,
      stopOnMatch: false,
    });

    // Rule 2: Priority 20 -> route to team 999
    const rule2Id = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: rule2Id,
      workspaceId: wsId,
      ruleKey: "rule_inbound_route",
      version: 1,
      name: "Inbound Route Rule",
      trigger: "message_received",
      priority: 20,
      condition: {
        fact: "lastMessage.direction",
        op: "eq",
        value: "inbound",
      },
      actions: [{ type: "route_to_team", teamId: "999" }],
      enabled: true,
      stopOnMatch: false,
    });

    const res = await evaluateRules({ trigger: "message_received", threadId: threadId.toString() }, ctx);

    expect(res.matched.length).toBe(2);
    expect(res.applied.length).toBe(2);
    expect(res.applied[0].outcome).toBe("applied");
    expect(res.applied[1].outcome).toBe("applied");

    // Check label applied
    const labels = await db
      .select()
      .from(engagementThreadLabels)
      .where(eq(engagementThreadLabels.threadId, threadId));
    expect(labels.some((l) => l.labelKey === "auto_received")).toBe(true);

    // Check assignment created
    const assignments = await db
      .select()
      .from(engagementAssignments)
      .where(eq(engagementAssignments.threadId, threadId));
    expect(assignments.some((a) => a.assignedTeamId?.toString() === "999")).toBe(true);
  });

  it("should respect dryRun mode without making database changes", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_dryrun_test",
      version: 1,
      name: "Dry Run Test Rule",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "dryrun_label" }],
      enabled: true,
      stopOnMatch: false,
    });

    const res = await evaluateRules(
      { trigger: "thread_opened", threadId: threadId.toString(), dryRun: true },
      ctx
    );

    expect(res.matched.length).toBe(1);
    expect(res.applied.length).toBe(0); // 0 applications

    // Verify 0 labels inserted
    const labels = await db
      .select()
      .from(engagementThreadLabels)
      .where(eq(engagementThreadLabels.threadId, threadId));
    expect(labels.length).toBe(0);
  });

  it("should stop on match when stopOnMatch is true", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    // Rule 1 with stopOnMatch = true
    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_stop_1",
      version: 1,
      name: "Stop Rule 1",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "first_stop_label" }],
      enabled: true,
      stopOnMatch: true,
    });

    // Rule 2 with lower priority
    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_stop_2",
      version: 1,
      name: "Stop Rule 2",
      trigger: "thread_opened",
      priority: 20,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "second_stop_label" }],
      enabled: true,
      stopOnMatch: false,
    });

    const res = await evaluateRules({ trigger: "thread_opened", threadId: threadId.toString() }, ctx);

    expect(res.matched.length).toBe(1);
    expect(res.applied.length).toBe(1);
    expect(res.matched[0].ruleKey).toBe("rule_stop_1");
  });
});
