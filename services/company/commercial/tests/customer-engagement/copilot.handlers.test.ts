import { describe, expect, it, beforeEach } from "vitest";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
} from "../../../shared/db/schema/customer-engagement";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
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

describe("Customer Engagement Copilot Handlers", () => {
  beforeEach(() => {
    setCustomCopilotRunner(async (payload) => {
      return { runId: `run_${Date.now()}_handler_test` };
    });
  });

  it("handles settings lifecycle and enforces fail-closed enablement via API", async () => {
    const user = await createTestSession({
      displayName: "Lead Agent",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;

    // 1. Initial settings -> enabled = false
    const initial = await getCopilotSettingsApi({ workspaceId, authorization });
    expect(initial.enabled).toBe(false);

    // 2. Enable without pinned spec -> throws failedPrecondition
    await expect(
      enableCopilotApi({ workspaceId, authorization })
    ).rejects.toThrow(/pin an agent spec/i);

    // 3. Update settings with pinned spec and matching eval evidence
    const updated = await updateCopilotSettingsApi({
      workspaceId,
      authorization,
      agentSpecId: "cosa.agents.customer_support",
      agentSpecVersion: "1.1.0",
      agentSpecHash: "hash_xyz_789",
      evalEvidenceRef: "evidence_run_1",
      evalEvidenceHash: "hash_xyz_789",
    });
    expect(updated.allowedAgentSpecId).toBe("cosa.agents.customer_support");

    // 4. Enable -> success
    const enabled = await enableCopilotApi({ workspaceId, authorization });
    expect(enabled.enabled).toBe(true);

    // 5. Disable -> success
    const disabled = await disableCopilotApi({ workspaceId, authorization });
    expect(disabled.enabled).toBe(false);
  });

  it("serves thread context, dispatches copilot, records feedback, and applies result callback", async () => {
    const user = await createTestSession({
      displayName: "Support Agent",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    // 1. Seed inbox & thread
    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "email",
      name: "Support Desk",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "urgent",
      correlationId: "corr-handler-test",
    });

    // 2. Get thread context
    const context = await getThreadContextApi({
      id: threadId.toString(),
      workspaceId,
      authorization,
    });
    expect(context.thread.id).toBe(threadId.toString());
    expect(context.thread.priority).toBe("urgent");

    // 3. Request copilot while disabled -> fails
    await expect(
      requestCopilotApi({
        id: threadId.toString(),
        intent: "summarize",
        workspaceId,
        authorization,
      })
    ).rejects.toThrow(/not enabled/i);

    // 4. Enable copilot
    await updateCopilotSettingsApi({
      workspaceId,
      authorization,
      agentSpecId: "cosa.agents.customer_support",
      agentSpecVersion: "1.1.0",
      agentSpecHash: "hash_xyz_789",
      evalEvidenceRef: "evidence_run_1",
      evalEvidenceHash: "hash_xyz_789",
    });
    await enableCopilotApi({ workspaceId, authorization });

    // 5. Request copilot -> success
    const reqRes = await requestCopilotApi({
      id: threadId.toString(),
      intent: "summarize",
      workspaceId,
      authorization,
    });
    expect(reqRes.invocationId).toBeDefined();
    expect(reqRes.runId).toBeDefined();

    // 6. Apply result without service token -> unauthenticated
    await expect(
      applyCopilotResultApi({
        runId: reqRes.runId,
        status: "completed",
        artifactRef: "art_123",
        serviceToken: "wrong-token",
      })
    ).rejects.toThrow(/unauthenticated|service token/i);

    // Apply result with valid service token -> success
    const applyRes = await applyCopilotResultApi({
      runId: reqRes.runId,
      status: "completed",
      artifactRef: "art_123",
      summaryRef: "summary_123",
      serviceToken: process.env.COSA_SERVICE_TOKEN || "local-dev-service-token",
    });
    expect(applyRes.success).toBe(true);

    // 7. Get invocation
    const inv = await getCopilotInvocationApi({
      id: reqRes.invocationId,
      workspaceId,
      authorization,
    });
    expect(inv.status).toBe("completed");
    expect(inv.artifactRef).toBe("art_123");

    // 8. Record feedback
    const fb = await recordCopilotFeedbackApi({
      id: reqRes.invocationId,
      feedback: "accepted",
      workspaceId,
      authorization,
    });
    expect(fb.feedback).toBe("accepted");
  });
});
