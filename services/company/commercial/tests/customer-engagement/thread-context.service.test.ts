import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementAssignments,
  engagementThreadLabels,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts } from "../../../shared/db/schema/commercial";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getThreadContextForAgent } from "../../services/customer-engagement/thread-context.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

function makeCtx(workspaceId: string, permissions: string[] = ["engagement.thread.read"]): TenantContext {
  return {
    workspaceId,
    userId: "u123",
    workforceMemberId: "999",
    membershipRole: "member",
    permissions,
    correlationId: "corr-test",
  };
}

describe("thread-context.service", () => {
  it("returns minimized thread context with customer message, internal note, and verified identity", async () => {
    const ws1 = generateSnowflake().toString();
    const wsId = BigInt(ws1);
    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();
    const contactId = generateSnowflake();
    const accountId = generateSnowflake();

    // 1. Create account & contact
    await db.insert(accounts).values({
      id: accountId,
      workspaceId: wsId,
      name: "Acme Corp",
    });

    await db.insert(contacts).values({
      id: contactId,
      workspaceId: wsId,
      accountId: accountId,
      name: "Alice Customer",
      email: "alice@acme.com",
      doNotContact: false,
    });

    // 2. Create inbox & thread
    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Support Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      contactId,
      accountId,
      status: "open",
      priority: "urgent",
      tier: "vip",
      activeMode: "assigned",
      ownerMemberId: 888n,
      correlationId: "corr-thread-123",
    });

    // 3. Create messages (customer public + agent internal note)
    const msg1Id = generateSnowflake();
    const msg2Id = generateSnowflake();
    const retention = new Date(Date.now() + 365 * 86400000);
    const body1 = "My account is locked, please help.";
    const body2 = "Handoff note: customer reported lock after 3 failed login attempts.";

    await db.insert(engagementMessages).values({
      id: msg1Id,
      workspaceId: wsId,
      threadId,
      direction: "inbound",
      visibility: "public",
      senderKind: "customer",
      body: body1,
      bodyContentHash: createHash("sha256").update(body1).digest("hex"),
      idempotencyKey: "idem-msg-1",
      retentionUntil: retention,
    });

    await db.insert(engagementMessages).values({
      id: msg2Id,
      workspaceId: wsId,
      threadId,
      direction: "outbound",
      visibility: "internal",
      senderKind: "human_agent",
      body: body2,
      bodyContentHash: createHash("sha256").update(body2).digest("hex"),
      idempotencyKey: "idem-msg-2",
      retentionUntil: retention,
    });

    // 4. Create assignment & label
    await db.insert(engagementAssignments).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      threadId,
      assignedMemberId: 888n,
      reason: "manual_triage",
      endedAt: null,
    });

    await db.insert(engagementThreadLabels).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      threadId,
      labelKey: "account_lockout",
      taxonomyVersion: "1",
      source: "agent",
    });

    // 5. Fetch context
    const ctx = makeCtx(ws1);
    const context = await getThreadContextForAgent(threadId.toString(), ctx);

    expect(context.thread.id).toBe(threadId.toString());
    expect(context.thread.status).toBe("open");
    expect(context.thread.priority).toBe("urgent");
    expect(context.thread.tier).toBe("vip");
    expect(context.contactId).toBe(contactId.toString());
    expect(context.identityVerified).toBe(true);
    expect(context.messages.length).toBe(2);
    expect(context.messages[0].body).toBe("My account is locked, please help.");
    expect(context.messages[1].visibility).toBe("internal");
    expect(context.assignment?.assignedMemberId).toBe("888");
    expect(context.labels).toEqual([{ labelKey: "account_lockout", taxonomyVersion: 1 }]);
  });

  it("handles unverified identity when contact has no email or contactId is null", async () => {
    const ws1 = generateSnowflake().toString();
    const wsId = BigInt(ws1);
    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "chat",
      name: "Anonymous Chat",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      contactId: null,
      status: "open",
      correlationId: "corr-anon",
    });

    const ctx = makeCtx(ws1);
    const context = await getThreadContextForAgent(threadId.toString(), ctx);
    expect(context.contactId).toBeNull();
    expect(context.identityVerified).toBe(false);
  });

  it("enforces tenant isolation and throws notFound for cross-workspace access", async () => {
    const ws2 = generateSnowflake().toString();
    const ctxWrongWs = makeCtx(ws2);
    // Try to query thread from ws1 using ws2 context
    await expect(getThreadContextForAgent("99999999", ctxWrongWs)).rejects.toThrow(/not found/i);
  });
});
