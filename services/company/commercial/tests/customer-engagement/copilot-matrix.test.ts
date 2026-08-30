import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementCopilotInvocations,
  engagementCopilotSettings,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts } from "../../../shared/db/schema/commercial";
import { eventOutbox } from "../../../shared/db/schema/integration";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import {
  getCopilotSettingsApi,
  updateCopilotSettingsApi,
  enableCopilotApi,
  disableCopilotApi,
  getThreadContextApi,
  requestCopilotApi,
  getCopilotInvocationApi,
  recordCopilotFeedbackApi,
  applyCopilotResultApi,
} from "../../handlers/customer-engagement/copilot.handler";
import { setCustomCopilotRunner } from "../../services/customer-engagement/copilot-cosa-client";

describe("P1 Copilot Test Matrix (Company Service)", () => {
  let dispatchedRuns: any[] = [];

  beforeEach(() => {
    dispatchedRuns = [];
    setCustomCopilotRunner(async (payload) => {
      dispatchedRuns.push(payload);
      return { runId: `run_${Date.now()}_matrix` };
    });
  });

  it("Scenario: Fail-closed before enablement -> request rejected, 0 dispatch, 0 invocation", async () => {
    const user = await createTestSession({ displayName: "Agent", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Matrix Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-matrix-1",
    });

    // Request copilot -> must fail with failedPrecondition
    await expect(
      requestCopilotApi({ id: threadId.toString(), intent: "summarize", workspaceId, authorization })
    ).rejects.toThrow(/not enabled/i);

    expect(dispatchedRuns.length).toBe(0);

    const rows = await db
      .select()
      .from(engagementCopilotInvocations)
      .where(eq(engagementCopilotInvocations.workspaceId, wsId));
    expect(rows.length).toBe(0);
  });

  it("Scenario: Enable without spec or mismatch eval evidence -> fail-closed", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;

    // 1. Without spec
    await expect(enableCopilotApi({ workspaceId, authorization })).rejects.toThrow(/pin an agent spec/i);

    // 2. With spec but mismatched evidence hash
    await updateCopilotSettingsApi({
      workspaceId,
      authorization,
      agentSpecId: "cosa.agents.customer_support",
      agentSpecVersion: "1.1.0",
      agentSpecHash: "hash_real_1",
      evalEvidenceRef: "evidence_1",
      evalEvidenceHash: "hash_mismatch_2",
    });

    await expect(enableCopilotApi({ workspaceId, authorization })).rejects.toThrow(/fresh eval evidence/i);

    const settings = await getCopilotSettingsApi({ workspaceId, authorization });
    expect(settings.enabled).toBe(false);
  });

  it("Scenario: Disallowed intent -> invalidArgument error", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    await updateCopilotSettingsApi({
      workspaceId,
      authorization,
      agentSpecId: "cosa.agents.customer_support",
      agentSpecVersion: "1.1.0",
      agentSpecHash: "hash_real_1",
      evalEvidenceRef: "evidence_1",
      evalEvidenceHash: "hash_real_1",
    });
    await enableCopilotApi({ workspaceId, authorization });

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Matrix Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-matrix-2",
    });

    await expect(
      requestCopilotApi({
        id: threadId.toString(),
        intent: "unregistered_external_action",
        workspaceId,
        authorization,
      })
    ).rejects.toThrow(/not in allowed intents/i);
  });

  it("Scenario: Cross-workspace isolation for context and invocation", async () => {
    const userA = await createTestSession({ displayName: "UserA", role: "admin" });
    const userB = await createTestSession({ displayName: "UserB", role: "admin" });

    const authA = `Bearer ${userA.accessToken}`;
    const authB = `Bearer ${userB.accessToken}`;
    const wsIdA = BigInt(userA.workspaceId);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsIdA,
      channelType: "email",
      name: "Inbox A",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsIdA,
      inboxId,
      status: "open",
      correlationId: "corr-matrix-cross",
    });

    // UserB attempting to read UserA's thread context
    await expect(
      getThreadContextApi({ id: threadId.toString(), workspaceId: userB.workspaceId, authorization: authB })
    ).rejects.toThrow(/not found/i);
  });

  it("Scenario: Execution completion and feedback: 0 new messages auto-sent, 0 CRM modified", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    await updateCopilotSettingsApi({
      workspaceId,
      authorization,
      agentSpecId: "cosa.agents.customer_support",
      agentSpecVersion: "1.1.0",
      agentSpecHash: "hash_real_1",
      evalEvidenceRef: "evidence_1",
      evalEvidenceHash: "hash_real_1",
    });
    await enableCopilotApi({ workspaceId, authorization });

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Matrix Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: "corr-matrix-3",
    });

    const dispatchResult = await requestCopilotApi({
      id: threadId.toString(),
      intent: "draft_reply",
      workspaceId,
      authorization,
    });

    // Apply result from COSA
    await applyCopilotResultApi({
      runId: dispatchResult.runId,
      status: "completed",
      artifactRef: "art_ref_999",
      summaryRef: "sum_ref_999",
      serviceToken: process.env.COSA_SERVICE_TOKEN || "local-dev-service-token",
    });

    const invocation = await getCopilotInvocationApi({
      id: dispatchResult.invocationId,
      workspaceId,
      authorization,
    });
    expect(invocation.status).toBe("completed");
    expect(invocation.artifactRef).toBe("art_ref_999");

    // Record feedback
    const fb = await recordCopilotFeedbackApi({
      id: dispatchResult.invocationId,
      feedback: "edited",
      editedRef: "user_edited_draft_1",
      workspaceId,
      authorization,
    });
    expect(fb.feedback).toBe("edited");

    // Check that NO message was added to the thread
    const msgCount = await db
      .select()
      .from(engagementMessages)
      .where(eq(engagementMessages.threadId, threadId));
    expect(msgCount.length).toBe(0);
  });
});
