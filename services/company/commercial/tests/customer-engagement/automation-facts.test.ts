import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementThreadLabels,
  engagementThreadOutcomes,
  engagementDecisionRequests,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts, customers } from "../../../shared/db/schema/commercial";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  buildAutomationFacts,
  FACT_KEYS,
} from "../../services/customer-engagement/automation/facts";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Automation Facts Model Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_facts_test",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_facts_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Facts Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should extract all structured facts accurately for a thread", async () => {
    const threadId = generateSnowflake();
    const contactId = generateSnowflake();
    const accountId = generateSnowflake();
    const customerId = generateSnowflake();
    const messageId = generateSnowflake();
    const labelId = generateSnowflake();

    // 1. Account & Contact & Customer
    await db.insert(accounts).values({
      id: accountId,
      workspaceId: wsId,
      name: "Acme High Priority",
      sizeSegment: "enterprise",
    });

    await db.insert(contacts).values({
      id: contactId,
      workspaceId: wsId,
      accountId,
      name: "VIP Contact",
      phone: "+84900111222",
      doNotContact: true,
    });

    await db.insert(customers).values({
      id: customerId,
      workspaceId: wsId,
      accountId,
      healthStatus: "AT_RISK",
    });

    // 2. Thread
    const firstResponseDueAt = new Date(Date.now() - 30 * 60 * 1000); // 30m in the past -> breached
    const resolutionDueAt = new Date(Date.now() + 120 * 60 * 1000); // 2h in future

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      contactId,
      accountId,
      customerId,
      status: "open",
      priority: "urgent",
      tier: "vip",
      activeMode: "team_queue",
      escalationLevel: 1,
      firstResponseDueAt,
      resolutionDueAt,
      correlationId: `corr_${threadId}`,
    });

    // 3. Message
    await db.insert(engagementMessages).values({
      id: messageId,
      workspaceId: wsId,
      threadId,
      direction: "inbound",
      visibility: "customer",
      senderKind: "customer",
      body: "Tôi cần trợ giúp khẩn cấp",
      bodyContentHash: "hash_facts",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_f_${messageId}`,
    });

    // 4. Label
    await db.insert(engagementThreadLabels).values({
      id: labelId,
      workspaceId: wsId,
      threadId,
      labelKey: "critical_issue",
      taxonomyVersion: "1",
      source: "manual",
    });

    // 5. CSAT Outcome
    await db.insert(engagementThreadOutcomes).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      threadId,
      csatScore: 2,
      csatRecordedAt: new Date(Date.now() - 10 * 60 * 1000),
    });

    // 6. Decision Request
    await db.insert(engagementDecisionRequests).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      threadId,
      requestType: "refund",
      status: "pending_approval",
      requestedByActor: { kind: "user", id: "user_1" },
      requestedByWorkforceMemberId: generateSnowflake(),
      authorityKey: "refund_auth",
      authorityVersion: 1,
      approvalPolicySnapshot: {},
      correlationId: `corr_dr_${threadId}`,
    });

    const facts = await buildAutomationFacts(threadId.toString(), ctx);

    expect(facts.thread.status).toBe("open");
    expect(facts.thread.priority).toBe("urgent");
    expect(facts.thread.tier).toBe("vip");
    expect(facts.thread.activeMode).toBe("team_queue");
    expect(facts.thread.escalationLevel).toBe(1);
    expect(facts.thread.firstResponded).toBe(false);
    expect(facts.thread.hasOpenDecisionRequest).toBe(true);

    expect(facts.inbox.channelType).toBe("zalo");

    expect(facts.sla.firstResponseBreached).toBe(true);
    expect(facts.sla.resolutionBreached).toBe(false);

    expect(facts.contact.present).toBe(true);
    expect(facts.contact.doNotContact).toBe(true);

    expect(facts.customer.present).toBe(true);
    expect(facts.customer.healthStatus).toBe("AT_RISK");

    expect(facts.lastMessage.direction).toBe("inbound");
    expect(facts.lastMessage.visibility).toBe("customer");

    expect(facts.csat.latestScore).toBe(2);
    expect(facts.labels).toContain("critical_issue");
  });

  it("should enforce FACT_KEYS completeness", () => {
    expect(FACT_KEYS.has("thread.status")).toBe(true);
    expect(FACT_KEYS.has("sla.firstResponseBreached")).toBe(true);
    expect(FACT_KEYS.has("customer.healthStatus")).toBe(true);
    expect(FACT_KEYS.has("csat.latestScore")).toBe(true);
    expect(FACT_KEYS.has("labels")).toBe(true);
  });
});
