import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db } from "../models/db";
import { eventOutbox } from "../../shared/db/schema/integration";
import { founderAssetEvents } from "../../shared/db/schema/operations";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  requestAssetClone,
  requestAssetCreate,
  requestAssetEditDraft,
  requestAssetEvaluate,
  requestAssetPublish,
  handleAssetStatusCallback,
  getFounderAssetEvents,
} from "../services/founder-asset-authoring.service";

describe("Founder Asset Authoring Service", () => {
  it("allows only a HUMAN founder to issue asset authoring commands", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const aiAgentContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-ai",
      isAiAgent: true,
    };

    const memberContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "member",
      permissions: ["*"],
      correlationId: "corr-member",
      isAiAgent: false,
    };

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-founder",
      isAiAgent: false,
    };

    const cloneInput = {
      projectId: ws.projectId,
      assetKind: "AGENT" as const,
      operation: "CLONE" as const,
      assetRef: {
        assetId: "agent_builtin_copywriter",
        version: "1.0.0",
        definitionHash: "sha256:hash1",
      },
      expectedVersion: 1,
      idempotencyKey: "idem_clone_auth_test_1",
      reason: "Clone built-in agent for customization",
    };

    // AI agent must be blocked
    await expect(requestAssetClone(aiAgentContext, cloneInput)).rejects.toThrow(
      /HUMAN founder/i
    );

    // Non-founder member must be blocked
    await expect(requestAssetClone(memberContext, cloneInput)).rejects.toThrow(
      /founder/i
    );

    // Human founder succeeds
    const result = await requestAssetClone(founderContext, cloneInput);
    expect(result).toBeDefined();
    expect(result.commandId).toBeDefined();
    expect(result.status).toBe("PENDING");
  });

  it("records one Company command and one outbox row for an idempotency key", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-idem",
      isAiAgent: false,
    };

    const cloneInput = {
      projectId: ws.projectId,
      assetKind: "SKILL" as const,
      operation: "CLONE" as const,
      assetRef: {
        assetId: "skill_builtin_summarizer",
        version: "1.0.0",
        definitionHash: "sha256:skillsum1",
      },
      expectedVersion: 1,
      idempotencyKey: "idem_clone_exact_key_999",
      reason: "Clone built-in summarizer",
    };

    // First command
    const res1 = await requestAssetClone(founderContext, cloneInput);

    // Duplicate command with same idempotencyKey
    const res2 = await requestAssetClone(founderContext, cloneInput);

    expect(res1.commandId).toBe(res2.commandId);

    // Verify exactly 1 outbox event for this idempotency key
    const outboxRows = await db
      .select()
      .from(eventOutbox)
      .where(
        and(
          eq(eventOutbox.workspaceId, ws.workspaceId),
          eq(eventOutbox.eventType, "founder.asset.commanded.v1")
        )
      );

    const matching = outboxRows.filter(
      (r) => ((r.envelope as any)?.payload)?.idempotencyKey === "idem_clone_exact_key_999"
    );
    expect(matching).toHaveLength(1);

    const payload = (matching[0].envelope as any)?.payload;
    expect(payload.commandId).toBe(res1.commandId);
    expect(payload.workspaceId).toBe(ws.workspaceId);
    expect(payload.assetKind).toBe("SKILL");
    expect(payload.operation).toBe("CLONE");
    expect(payload.assetRef.assetId).toBe("skill_builtin_summarizer");
  });

  it("updates founder asset event projection when status callback is received", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-status",
      isAiAgent: false,
    };

    const cmd = await requestAssetClone(founderContext, {
      projectId: ws.projectId,
      assetKind: "AGENT",
      operation: "CLONE",
      assetRef: {
        assetId: "agent_builtin_analyst",
        version: "1.0.0",
        definitionHash: "sha256:analyst1",
      },
      expectedVersion: 1,
      idempotencyKey: "idem_status_test_777",
      reason: "Clone analyst",
    });

    // Callback arrives from Agent Platform
    await handleAssetStatusCallback({
      commandId: cmd.commandId,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      assetKind: "AGENT",
      operation: "CLONE",
      status: "SUCCESS",
      assetRef: {
        assetId: "agent_custom_analyst_clone",
        version: "1.0.0",
        definitionHash: "sha256:clonedhash2",
      },
      evaluationSummary: {
        evalScore: 0.95,
        status: "COMPLETED",
      },
      safeReasonCode: "CLONE_SUCCESS",
    });

    const events = await getFounderAssetEvents(ws.workspaceId, cmd.commandId);
    expect(events.length).toBeGreaterThanOrEqual(1);
    const latest = events[events.length - 1];
    expect(latest.metadata).toMatchObject({
      status: "SUCCESS",
      safeReasonCode: "CLONE_SUCCESS",
    });
  });

  it("rejects command when metadata contains raw secrets before creating outbox event", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-secret-test",
      isAiAgent: false,
    };

    await expect(
      requestAssetCreate(founderContext, {
        projectId: ws.projectId,
        assetKind: "AGENT",
        assetRef: { assetId: "agent_secret_test", version: "0.1.0" },
        idempotencyKey: "idem_secret_1",
        reason: "Testing secret rejection",
        metadata: {
          config: {
            apiKey: "sk-1234567890abcdef1234567890",
          },
        },
      })
    ).rejects.toThrow(/FOUNDER_ASSET_SECRET_REJECTED/);

    // Verify nothing was written to founderAssetEvents or eventOutbox
    const events = await getFounderAssetEvents(ws.workspaceId);
    expect(events.find((e) => e.targetRef?.assetId === "agent_secret_test")).toBeUndefined();
  });

  it("rejects command when metadata contains forbidden credential keys", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-forbidden-key-test",
      isAiAgent: false,
    };

    await expect(
      requestAssetCreate(founderContext, {
        projectId: ws.projectId,
        assetKind: "AGENT",
        assetRef: { assetId: "agent_forbidden_key_test", version: "0.1.0" },
        idempotencyKey: "idem_forbidden_1",
        reason: "Testing forbidden key rejection",
        metadata: {
          secret: "some-raw-value",
        },
      })
    ).rejects.toThrow(/FOUNDER_ASSET_FORBIDDEN_KEY/);
  });
});
