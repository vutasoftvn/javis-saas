import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementCopilotInvocations,
} from "../../../shared/db/schema/customer-engagement";
import { eventOutbox } from "../../../shared/db/schema/integration";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  updateCopilotSettings,
  enableCopilot,
} from "../../services/customer-engagement/copilot-settings.service";
import {
  requestCopilot,
  getCopilotInvocation,
  applyCopilotResult,
  recordCopilotFeedback,
} from "../../services/customer-engagement/copilot.service";
import { setCustomCopilotRunner } from "../../services/customer-engagement/copilot-cosa-client";
import type { TenantContext } from "../../../shared/types/tenant_context";

function makeCtx(workspaceId: string, permissions: string[] = ["engagement.copilot.request", "engagement.copilot.manage", "engagement.thread.read"]): TenantContext {
  return {
    workspaceId,
    userId: "u123",
    workforceMemberId: "999",
    membershipRole: "member",
    permissions,
    correlationId: "corr-test",
  };
}

describe("copilot.service", () => {
  let dispatchedRuns: any[] = [];

  beforeEach(() => {
    dispatchedRuns = [];
    setCustomCopilotRunner(async (payload) => {
      dispatchedRuns.push(payload);
      return { runId: `run_${Date.now()}_${Math.random().toString(16).slice(2, 10)}` };
    });
  });

  it("throws failedPrecondition and does not dispatch or insert when copilot is disabled", async () => {
    const wsIdStr = generateSnowflake().toString();
    const wsId = BigInt(wsIdStr);
    const ctx = makeCtx(wsIdStr);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-1",
    });

    await expect(requestCopilot(threadId.toString(), { intent: "summarize" }, ctx)).rejects.toThrow(
      /failedPrecondition|not enabled/i
    );

    expect(dispatchedRuns.length).toBe(0);

    const invocations = await db
      .select()
      .from(engagementCopilotInvocations)
      .where(eq(engagementCopilotInvocations.workspaceId, wsId));
    expect(invocations.length).toBe(0);
  });

  it("dispatches run, creates invocation row, and appends outbox event when copilot is enabled", async () => {
    const wsIdStr = generateSnowflake().toString();
    const wsId = BigInt(wsIdStr);
    const ctx = makeCtx(wsIdStr);

    // 1. Enable copilot with pinned spec and valid eval evidence
    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.1.0",
        agentSpecHash: "spec_hash_123",
        evalEvidenceRef: "eval_evidence_123",
        evalEvidenceHash: "spec_hash_123",
      },
      ctx
    );
    await enableCopilot(ctx);

    // 2. Create inbox and thread
    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-1",
    });

    // 3. Request copilot
    const result = await requestCopilot(threadId.toString(), { intent: "summarize" }, ctx);
    expect(result.invocationId).toBeDefined();
    expect(result.runId).toBeDefined();
    expect(dispatchedRuns.length).toBe(1);

    // 4. Verify invocation record
    const invocation = await getCopilotInvocation(result.invocationId, ctx);
    expect(invocation.status).toBe("dispatched");
    expect(invocation.intent).toBe("summarize");
    expect(invocation.agentSpecId).toBe("cosa.agents.customer_support");
    expect(invocation.agentSpecHash).toBe("spec_hash_123");

    // 5. Verify outbox event
    const outboxEvents = await db
      .select()
      .from(eventOutbox)
      .where(and(eq(eventOutbox.workspaceId, wsIdStr), eq(eventOutbox.eventType, "engagement.copilot.requested.v1")));
    expect(outboxEvents.length).toBe(1);
    expect(outboxEvents[0].aggregateId).toBe(threadId.toString());
  });

  it("applies copilot result callback and updates invocation status and artifact refs", async () => {
    const wsIdStr = generateSnowflake().toString();
    const wsId = BigInt(wsIdStr);
    const ctx = makeCtx(wsIdStr);

    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.1.0",
        agentSpecHash: "spec_hash_123",
        evalEvidenceRef: "eval_evidence_123",
        evalEvidenceHash: "spec_hash_123",
      },
      ctx
    );
    await enableCopilot(ctx);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-2",
    });

    const { invocationId, runId } = await requestCopilot(threadId.toString(), { intent: "draft_reply" }, ctx);

    // COSA calls applyCopilotResult
    await applyCopilotResult({
      runId,
      status: "completed",
      artifactRef: "artifact_blob_123",
      summaryRef: "summary_text_123",
    });

    const updated = await getCopilotInvocation(invocationId, ctx);
    expect(updated.status).toBe("completed");
    expect(updated.artifactRef).toBe("artifact_blob_123");
    expect(updated.summaryRef).toBe("summary_text_123");
  });

  it("records copilot feedback, emits feedback event, and does NOT insert message into thread", async () => {
    const wsIdStr = generateSnowflake().toString();
    const wsId = BigInt(wsIdStr);
    const ctx = makeCtx(wsIdStr);

    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.1.0",
        agentSpecHash: "spec_hash_123",
        evalEvidenceRef: "eval_evidence_123",
        evalEvidenceHash: "spec_hash_123",
      },
      ctx
    );
    await enableCopilot(ctx);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-3",
    });

    const { invocationId, runId } = await requestCopilot(threadId.toString(), { intent: "draft_reply" }, ctx);

    await applyCopilotResult({
      runId,
      status: "completed",
      artifactRef: "artifact_blob_123",
    });

    // Record feedback
    const feedbackRes = await recordCopilotFeedback(
      invocationId,
      { feedback: "accepted" },
      ctx
    );

    expect(feedbackRes.feedback).toBe("accepted");
    expect(feedbackRes.feedbackByWorkforceMemberId).toBe("999");
    expect(feedbackRes.feedbackAt).toBeDefined();

    // Verify feedback event in outbox
    const outboxEvents = await db
      .select()
      .from(eventOutbox)
      .where(and(eq(eventOutbox.workspaceId, wsIdStr), eq(eventOutbox.eventType, "engagement.copilot.feedback.v1")));
    expect(outboxEvents.length).toBe(1);

    // CRITICAL: verify no new message was auto-inserted into the thread
    const messages = await db
      .select()
      .from(engagementMessages)
      .where(eq(engagementMessages.threadId, threadId));
    expect(messages.length).toBe(0);
  });
});
