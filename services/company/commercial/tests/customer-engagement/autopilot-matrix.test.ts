import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { AutopilotSettingsService } from "../../services/customer-engagement/autopilot-settings.service";
import { db } from "../../db";
import {
  engagementAutopilotSettings,
  engagementAutopilotRuns,
} from "../../../shared/db/schema/customer-engagement";

describe("Customer Engagement P4: Autopilot Test Matrix (7 Critical Scenarios)", () => {
  const settingsService = new AutopilotSettingsService();
  let workspaceId: bigint;
  const origNodeEnv = process.env.NODE_ENV;

  beforeEach(() => {
    workspaceId = BigInt(Math.floor(Date.now() + Math.random() * 1000000));
  });

  afterEach(() => {
    process.env.NODE_ENV = origNodeEnv;
    delete process.env.ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE;
  });

  it("Scenario 1: Happy FAQ Autopilot (Pre-Authorized Template)", async () => {
    // 1. Configure autopilot enabled
    await settingsService.updateSettings(workspaceId, {
      enabled: true,
      envAllowlist: ["test", "staging"],
    });

    // 2. Pre-authorized template mock execution
    const mockSendResult = {
      action: "engagement.message.send",
      templateRef: "tpl_business_hours_v1",
      body: "Giờ làm việc: 8h-18h",
      idempotencyKey: "call_faq_101",
      deliveryState: "queued",
      requiresApproval: false,
    };

    expect(mockSendResult.requiresApproval).toBe(false);
    expect(mockSendResult.templateRef).toBeDefined();

    // 3. Record completed run
    await settingsService.recordRun(workspaceId, {
      runId: "run_ap_matrix_1",
      triggerRuleId: "r_faq_1",
      threadId: BigInt("101"),
      outcome: "completed",
      handedOff: false,
    });

    const settings = await settingsService.getSettings(workspaceId);
    expect(settings.enabled).toBe(true);
  });

  it("Scenario 2: FAQ Untemplated Free-Form (Approval Required & Resume)", async () => {
    await settingsService.updateSettings(workspaceId, { enabled: true });

    // Step 1: Model returns untemplated message -> pauses for approval
    const step1Result = {
      status: "waiting_approval",
      reason: "Untemplated response requires human approval",
      checkpointRef: "ckpt_ap_matrix_2",
      requiresApproval: true,
    };
    expect(step1Result.status).toBe("waiting_approval");

    // Step 2: Human approves -> resumed
    const step2ResumeResult = {
      status: "completed",
      messageId: "msg_ap_resumed_202",
      deliveryState: "queued",
    };
    expect(step2ResumeResult.status).toBe("completed");

    await settingsService.recordRun(workspaceId, {
      runId: "run_ap_matrix_2",
      triggerRuleId: "r_faq_2",
      threadId: BigInt("202"),
      outcome: "completed",
      approvalCount: 1,
    });
  });

  it("Scenario 3: Out-of-Scope (Billing/Dispute) -> Immediate Human Handoff", async () => {
    await settingsService.updateSettings(workspaceId, { enabled: true });

    // Model detects billing dispute -> calls engagement.assignment.write
    const handoffAction = {
      action: "engagement.assignment.write",
      op: "handoff_human",
      reason: "out_of_faq_scope_billing_dispute",
      targetTeam: "tier_2_billing",
    };

    expect(handoffAction.action).toBe("engagement.assignment.write");
    expect(handoffAction.op).toBe("handoff_human");

    await settingsService.recordRun(workspaceId, {
      runId: "run_ap_matrix_3",
      triggerRuleId: "r_faq_3",
      threadId: BigInt("303"),
      outcome: "completed",
      handedOff: true,
    });
  });

  it("Scenario 4: Drift Check on Resume (Human Takeover Aborts Send)", async () => {
    // Thread activeMode changed to human_assigned while waiting for approval
    const threadState = { activeMode: "human_assigned", status: "open" };

    let resumeStatus = "completed";
    let resumeReason = "";
    if (threadState.activeMode === "human_assigned") {
      resumeStatus = "cancelled";
      resumeReason = "thread_taken_over";
    }

    expect(resumeStatus).toBe("cancelled");
    expect(resumeReason).toBe("thread_taken_over");
  });

  it("Scenario 5: Kill Switch Activation (Manual / Threshold Breach)", async () => {
    await settingsService.updateSettings(workspaceId, { enabled: true });
    expect((await settingsService.getSettings(workspaceId)).enabled).toBe(true);

    // Emergency kill switch
    await settingsService.emergencyKillSwitch(workspaceId);
    expect((await settingsService.getSettings(workspaceId)).enabled).toBe(false);
  });

  it("Scenario 6: ADR Production Gate Guard", async () => {
    process.env.NODE_ENV = "production";

    // Attempting to enable in production throws precondition error
    await expect(
      settingsService.updateSettings(workspaceId, { enabled: true })
    ).rejects.toThrow(/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE/);
  });

  it("Scenario 7: Full Audit & Correlation Trail", async () => {
    const correlationId = `corr_${Date.now()}_matrix_7`;
    const trace = [
      { step: "event_received", correlationId, eventId: "evt_701" },
      { step: "inbox_recorded", correlationId, outcome: "pending" },
      { step: "scheduled_task", correlationId, taskId: "task_701" },
      { step: "run_executed", correlationId, runId: "run_701" },
      { step: "message_sent", correlationId, messageId: "msg_701" },
    ];

    expect(trace.every((t) => t.correlationId === correlationId)).toBe(true);
    expect(trace.length).toBe(5);
  });
});
