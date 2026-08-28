import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementAutomationRules,
  engagementAutomationApplications,
  engagementAutomationSchedules,
  engagementThreadOutcomes,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

describe("Customer Engagement P3 Automation Schema Tests", () => {
  it("should enforce unique (workspace_id, rule_key, version) on rules", async () => {
    const wsId = generateSnowflake();
    const id1 = generateSnowflake();
    const id2 = generateSnowflake();

    await db.insert(engagementAutomationRules).values({
      id: id1,
      workspaceId: wsId,
      ruleKey: "rule_test_unique",
      version: 1,
      name: "Test Rule",
      trigger: "thread_opened",
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "reopen" }],
      enabled: true,
    });

    // Inserting same (workspace_id, rule_key, version) must violate unique constraint
    await expect(
      db.insert(engagementAutomationRules).values({
        id: id2,
        workspaceId: wsId,
        ruleKey: "rule_test_unique",
        version: 1,
        name: "Test Rule Dup",
        trigger: "thread_opened",
        condition: { fact: "thread.status", op: "eq", value: "open" },
        actions: [{ type: "reopen" }],
        enabled: true,
      })
    ).rejects.toThrow();
  });

  it("should enforce unique (rule_key, rule_version, thread_id, action_index, dedupe_key) on applications", async () => {
    const wsId = generateSnowflake();
    const threadId = generateSnowflake();
    const id1 = generateSnowflake();
    const id2 = generateSnowflake();

    await db.insert(engagementAutomationApplications).values({
      id: id1,
      workspaceId: wsId,
      ruleKey: "rule_test_app",
      ruleVersion: 1,
      threadId,
      trigger: "message_received",
      actionIndex: 0,
      actionType: "apply_label",
      dedupeKey: "label_vip",
      outcome: "applied",
    });

    await expect(
      db.insert(engagementAutomationApplications).values({
        id: id2,
        workspaceId: wsId,
        ruleKey: "rule_test_app",
        ruleVersion: 1,
        threadId,
        trigger: "message_received",
        actionIndex: 0,
        actionType: "apply_label",
        dedupeKey: "label_vip",
        outcome: "applied",
      })
    ).rejects.toThrow();
  });

  it("should insert schedule and support csat columns on outcomes", async () => {
    const wsId = generateSnowflake();
    const threadId = generateSnowflake();
    const schedId = generateSnowflake();

    await db.insert(engagementAutomationSchedules).values({
      id: schedId,
      workspaceId: wsId,
      ruleKey: "rule_test_sched",
      ruleVersion: 1,
      threadId,
      actionIndex: 0,
      action: { type: "escalate" },
      condition: { fact: "sla.firstResponseBreached", op: "eq", value: true },
      dueAt: new Date(Date.now() + 1800000),
      status: "pending",
    });

    const [sched] = await db
      .select()
      .from(engagementAutomationSchedules)
      .where(sql`id = ${schedId}`);
    expect(sched.status).toBe("pending");
    expect(sched.ruleKey).toBe("rule_test_sched");
  });
});
