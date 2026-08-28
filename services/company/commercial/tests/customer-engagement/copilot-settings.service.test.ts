import { describe, expect, it, beforeEach } from "vitest";
import { db } from "../../db";
import { engagementCopilotSettings } from "../../../shared/db/schema/customer-engagement";
import {
  getCopilotSettings,
  updateCopilotSettings,
  enableCopilot,
  disableCopilot,
  assertCopilotUsable,
} from "../../services/customer-engagement/copilot-settings.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

import { generateSnowflake } from "../../../shared/services/snowflake.service";

function makeCtx(workspaceId: string, permissions: string[] = ["engagement.copilot.manage", "engagement.copilot.request"]): TenantContext {
  return {
    workspaceId,
    userId: "u123",
    workforceMemberId: "999",
    membershipRole: "member",
    permissions,
    correlationId: "corr-test",
  };
}

describe("copilot-settings.service", () => {
  let ws1: string;
  let ws2: string;

  beforeEach(() => {
    ws1 = generateSnowflake().toString();
    ws2 = generateSnowflake().toString();
  });

  it("getCopilotSettings returns default settings (enabled: false) if row does not exist", async () => {
    const ctx = makeCtx(ws1);
    const settings = await getCopilotSettings(ctx);
    expect(settings.workspaceId).toBe(ws1);
    expect(settings.enabled).toBe(false);
    expect(settings.allowedIntents).toEqual(["summarize", "draft_reply", "extract_facts", "sales_signal"]);
  });

  it("enableCopilot throws failedPrecondition when no agent spec is pinned", async () => {
    const ctx = makeCtx(ws1);
    await expect(enableCopilot(ctx)).rejects.toThrow(/pin an agent spec/i);
  });

  it("enableCopilot throws failedPrecondition when eval evidence is missing or hash mismatch", async () => {
    const ctx = makeCtx(ws1);
    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.0.0",
        agentSpecHash: "hash_abc_123",
        evalEvidenceRef: "eval_run_999",
        evalEvidenceHash: "different_hash_456",
      },
      ctx
    );

    await expect(enableCopilot(ctx)).rejects.toThrow(/fresh eval evidence/i);
  });

  it("enableCopilot succeeds when spec is pinned and eval evidence hash matches spec hash", async () => {
    const ctx = makeCtx(ws1);
    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.0.0",
        agentSpecHash: "hash_abc_123",
        evalEvidenceRef: "eval_run_999",
        evalEvidenceHash: "hash_abc_123",
      },
      ctx
    );

    const enabled = await enableCopilot(ctx);
    expect(enabled.enabled).toBe(true);
    expect(enabled.allowedAgentSpecId).toBe("cosa.agents.customer_support");
  });

  it("disableCopilot disables copilot unconditionally", async () => {
    const ctx = makeCtx(ws1);
    const disabled = await disableCopilot(ctx);
    expect(disabled.enabled).toBe(false);
  });

  it("assertCopilotUsable checks enablement and allowed intents", async () => {
    const ctx = makeCtx(ws1);
    // When disabled -> failedPrecondition
    await expect(assertCopilotUsable("summarize", ctx)).rejects.toThrow(/failedPrecondition|disabled|not enabled/i);

    // Pin spec & evidence then enable
    await updateCopilotSettings(
      {
        agentSpecId: "cosa.agents.customer_support",
        agentSpecVersion: "1.0.0",
        agentSpecHash: "hash_abc_123",
        evalEvidenceRef: "eval_run_999",
        evalEvidenceHash: "hash_abc_123",
      },
      ctx
    );
    await enableCopilot(ctx);

    // Allowed intent -> passes
    const usable = await assertCopilotUsable("summarize", ctx);
    expect(usable.enabled).toBe(true);

    // Disallowed intent -> invalidArgument
    await expect(assertCopilotUsable("unauthorized_intent_action", ctx)).rejects.toThrow(/invalidArgument|not in allowed intents/i);
  });

  it("isolates settings between workspaces", async () => {
    const ctx1 = makeCtx(ws1);
    const ctx2 = makeCtx(ws2);

    const s1 = await getCopilotSettings(ctx1);
    const s2 = await getCopilotSettings(ctx2);
    expect(s1.workspaceId).toBe(ws1);
    expect(s2.workspaceId).toBe(ws2);
  });
});
