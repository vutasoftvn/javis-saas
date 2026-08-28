import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementAutomationRules,
  engagementThreadLabels,
  engagementThreadOutcomes,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { recordCsat } from "../../services/customer-engagement/csat.service";
import { evaluateRulesSafe } from "../../services/customer-engagement/automation/evaluator";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Automation Triggers & CSAT Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_trig_test",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_trig_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Triggers Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should record CSAT, trigger csat_recorded rule and escalate on low score", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    // Seed CSAT Rule: If csat.latestScore <= 2 -> escalate
    await db.insert(engagementAutomationRules).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      ruleKey: "rule_low_csat_escalate",
      version: 1,
      name: "Low CSAT Escalate Rule",
      trigger: "csat_recorded",
      priority: 10,
      condition: {
        fact: "csat.latestScore",
        op: "lte",
        value: 2,
      },
      actions: [{ type: "escalate" }],
      enabled: true,
      stopOnMatch: false,
    });

    const res = await recordCsat(threadId.toString(), { score: 1, comment: "Rất không hài lòng" }, ctx);
    expect(res.outcomeId).toBeDefined();

    // Verify outcome persisted in DB
    const [outcome] = await db
      .select()
      .from(engagementThreadOutcomes)
      .where(eq(engagementThreadOutcomes.threadId, threadId));
    expect(outcome.csatScore).toBe(1);
    expect(outcome.csatRecordedAt).toBeDefined();

    // Verify thread escalation level increased to 1
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(1);
  });

  it("should isolate rule errors without throwing in evaluateRulesSafe", async () => {
    // evaluateRulesSafe should not throw even if threadId doesn't exist
    await expect(
      evaluateRulesSafe({ trigger: "thread_opened", threadId: "999999999999999" }, ctx)
    ).resolves.not.toThrow();
  });
});
