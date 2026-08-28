import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementAutomationRules,
  engagementAutomationSchedules,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { runHousekeepingTick } from "../../services/customer-engagement/housekeeping.service";

describe("Delayed Automation Schedules Housekeeping Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Delayed Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should skip delayed schedule if condition changed before due", async () => {
    const threadId = generateSnowflake();
    // Thread has firstResponseAt set -> condition fact `thread.firstResponded` is true
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      firstResponseAt: new Date(),
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_cond",
      version: 1,
      name: "Delayed Escalate",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.firstResponded", op: "eq", value: false },
      actions: [{ type: "escalate" }],
      enabled: true,
      stopOnMatch: false,
    });

    const schedId = generateSnowflake();
    await db.insert(engagementAutomationSchedules).values({
      id: schedId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_cond",
      ruleVersion: 1,
      threadId,
      actionIndex: 0,
      action: { type: "escalate" },
      condition: { fact: "thread.firstResponded", op: "eq", value: false },
      dueAt: new Date(Date.now() - 60000), // Due 1 minute ago
      status: "pending",
    });

    await runHousekeepingTick(10);

    const [sched] = await db
      .select()
      .from(engagementAutomationSchedules)
      .where(eq(engagementAutomationSchedules.id, schedId));
    expect(sched.status).toBe("skipped");
    expect(sched.skipReason).toBe("condition_changed");

    // Thread escalation level remains 0
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(0);
  });

  it("should apply delayed action when condition is still true and rule enabled", async () => {
    const threadId = generateSnowflake();
    // Thread has not responded yet -> firstResponseAt is null
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      firstResponseAt: null,
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_ok",
      version: 1,
      name: "Delayed Escalate OK",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.firstResponded", op: "eq", value: false },
      actions: [{ type: "escalate" }],
      enabled: true,
      stopOnMatch: false,
    });

    const schedId = generateSnowflake();
    await db.insert(engagementAutomationSchedules).values({
      id: schedId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_ok",
      ruleVersion: 1,
      threadId,
      actionIndex: 0,
      action: { type: "escalate" },
      condition: { fact: "thread.firstResponded", op: "eq", value: false },
      dueAt: new Date(Date.now() - 60000), // Due 1 minute ago
      status: "pending",
    });

    await runHousekeepingTick(10);

    const [sched] = await db
      .select()
      .from(engagementAutomationSchedules)
      .where(eq(engagementAutomationSchedules.id, schedId));
    expect(sched.status).toBe("done");

    // Thread escalation level increased to 1
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(1);
  });

  it("should skip delayed schedule if human took over the thread before due", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      activeMode: "human_assigned", // Human took over!
      ownerMemberId: generateSnowflake(),
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_takeover",
      version: 1,
      name: "Delayed Escalate Takeover",
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
      ruleKey: "rule_delayed_takeover",
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

  it("should skip delayed schedule if rule was disabled before due", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    const ruleId = generateSnowflake();
    await db.insert(engagementAutomationRules).values({
      id: ruleId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_disabled",
      version: 1,
      name: "Disabled Rule",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "escalate" }],
      enabled: false, // Rule disabled!
      stopOnMatch: false,
    });

    const schedId = generateSnowflake();
    await db.insert(engagementAutomationSchedules).values({
      id: schedId,
      workspaceId: wsId,
      ruleKey: "rule_delayed_disabled",
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
    expect(sched.skipReason).toBe("rule_disabled");
  });
});
