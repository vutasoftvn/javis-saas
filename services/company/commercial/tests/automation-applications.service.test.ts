import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, schema } from "../models/db";
import { listThreadAutomationApplications } from "../services/customer-engagement/automation/applications.service";

describe("Automation Applications Service", () => {
  beforeEach(async () => {
    await db.delete(schema.engagementAutomationApplications);
  });

  afterEach(async () => {
    await db.delete(schema.engagementAutomationApplications);
  });

  it("listThreadAutomationApplications returns applications for workspace and thread", async () => {
    const wsId = BigInt("100");
    const threadId = BigInt("200");

    // Insert test application
    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("1"),
        workspaceId: wsId,
        threadId,
        ruleKey: "rule_001",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "send_message",
        dedupeKey: "dedup_1",
        outcome: "succeeded",
      });

    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "200",
    });

    expect(result.applications.length).toBe(1);
    expect(result.applications[0].ruleKey).toBe("rule_001");
    expect(result.applications[0].actionType).toBe("send_message");
  });

  it("listThreadAutomationApplications returns empty for non-existent thread", async () => {
    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "999",
    });

    expect(result.applications).toEqual([]);
  });

  it("listThreadAutomationApplications filters by workspace", async () => {
    const wsId1 = BigInt("100");
    const wsId2 = BigInt("101");
    const threadId = BigInt("200");

    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("1"),
        workspaceId: wsId1,
        threadId,
        ruleKey: "rule_001",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "send_message",
        dedupeKey: "dedup_1",
        outcome: "succeeded",
      });

    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("2"),
        workspaceId: wsId2,
        threadId,
        ruleKey: "rule_002",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "assign_thread",
        dedupeKey: "dedup_2",
        outcome: "succeeded",
      });

    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "200",
    });

    expect(result.applications.length).toBe(1);
    expect(result.applications[0].ruleKey).toBe("rule_001");
  });
});
