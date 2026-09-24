import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  createTestWorkspaceWithMember,
  createSecondWorkspace,
  makeTestTenantContext,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  createDraftDeliberation,
  frameDeliberation,
  recordExecutiveAnalysisCallback,
  getDeliberation,
} from "../services/executive-deliberation.service";
import {
  activateWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";

import { computeDeploymentPinHash, computeOverlayPinHash } from "../services/executive-pin-hash";
import type { SelectedAdvisorExecutionPin } from "../services/executive-deliberation.service";

// COSA Control Plane là app khác — giả lập đúng catalog generated (xem executive-deliberation.service.test.ts).
vi.mock("../services/advisor-overlay.client", () => ({
  fetchAdvisorOverlayIdentity: vi.fn(async (_ws: string, roleKey: string) => {
    const { ADVISOR_OVERLAY_CATALOG: catalog } = await import(
      "../../shared/contracts/executive-advisor-overlays.generated"
    );
    return catalog[roleKey];
  }),
}));

async function pinHashes(ctx: TenantContext, projectId: string, delibId: string, roleKey: string) {
  const details = await getDeliberation(ctx, projectId, delibId);
  const pin = (details.activeFrame?.selectedRoles as SelectedAdvisorExecutionPin[]).find(
    (r) => r.roleKey === roleKey
  )!;
  return {
    deployment_pin_hash: computeDeploymentPinHash(pin.deployment),
    overlay_pin_hash: computeOverlayPinHash(pin.overlay),
  };
}

describe("Executive Deliberation Callback & Transitions", () => {
  let founderCtx: TenantContext;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;

    // Deploy finance and marketing agents (V2), then activate CFO and CMO office
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "marketing");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
  });

  it("accepts a callback once and is idempotent on duplicate submissions", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Pricing Strategy Evaluation",
    });

    await frameDeliberation(founderCtx, projectId, draft.id, {
      question: "Should we increase base tier to $49/mo?",
      roleKeys: ["cfo", "cmo"],
    });

    const callbackPayload = {
      kind: "executive.analysis.completed.v1",
      deliberation_id: draft.id,
      frame_version: 1,
      role_key: "cfo",
      ...(await pinHashes(founderCtx, projectId, draft.id, "cfo")),
      descriptor: {
        run_id: "run-cfo-1",
        conclusion: "Financially sound, expected ARR increase 25%.",
        confidence: "HIGH",
        evidence_claims: [],
      },
    };

    // First submission
    const res1 = await recordExecutiveAnalysisCallback(
      founderCtx.workspaceId,
      projectId,
      draft.id,
      callbackPayload
    );
    expect(res1.roleKey).toBe("cfo");
    expect(res1.status).toBe("COMPLETED");

    // Check deliberation is still ANALYZING (waiting for cmo)
    const delibMid = await getDeliberation(founderCtx, projectId, draft.id);
    expect(delibMid.state).toBe("ANALYZING");

    // Second submission (duplicate / retry)
    const res2 = await recordExecutiveAnalysisCallback(
      founderCtx.workspaceId,
      projectId,
      draft.id,
      callbackPayload
    );
    expect(res2.id).toBe(res1.id);
    expect(res2.status).toBe("COMPLETED");

    // Now submit cmo callback
    const cmoPayload = {
      kind: "executive.analysis.completed.v1",
      deliberation_id: draft.id,
      frame_version: 1,
      role_key: "cmo",
      ...(await pinHashes(founderCtx, projectId, draft.id, "cmo")),
      descriptor: {
        run_id: "run-cmo-1",
        conclusion: "Marketing conversion might drop 10%, but net positive.",
        confidence: "MEDIUM",
        evidence_claims: [],
      },
    };
    const resCmo = await recordExecutiveAnalysisCallback(
      founderCtx.workspaceId,
      projectId,
      draft.id,
      cmoPayload
    );
    expect(resCmo.status).toBe("COMPLETED");

    // When all pinned roles complete, transition to AWAITING_FOUNDER
    const delibFinal = await getDeliberation(founderCtx, projectId, draft.id);
    expect(delibFinal.state).toBe("AWAITING_FOUNDER");
    expect(delibFinal.analyses).toHaveLength(2);
  });

  it("rejects callback for wrong project (cross-project fencing)", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Cross-project check",
    });
    await frameDeliberation(founderCtx, projectId, draft.id, {
      question: "Cross project test question",
      roleKeys: ["cfo"],
    });

    const callbackPayload = {
      kind: "executive.analysis.completed.v1",
      deliberation_id: draft.id,
      frame_version: 1,
      role_key: "cfo",
      ...(await pinHashes(founderCtx, projectId, draft.id, "cfo")),
      descriptor: { conclusion: "Ok" },
    };

    // Submitting with foreignProjectId should throw not found / mismatch
    await expect(
      recordExecutiveAnalysisCallback(
        founderCtx.workspaceId,
        foreignProjectId,
        draft.id,
        callbackPayload
      )
    ).rejects.toThrow();
  });

  it("rejects callback if deliberation was cancelled", async () => {
    const { cancelDeliberation } = await import("../services/executive-deliberation.service");
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Cancellation check",
    });
    await frameDeliberation(founderCtx, projectId, draft.id, {
      question: "Will this be cancelled?",
      roleKeys: ["cfo"],
    });

    // Cancel the deliberation
    await cancelDeliberation(founderCtx, projectId, draft.id, {
      reason: "No longer needed",
    });

    const callbackPayload = {
      kind: "executive.analysis.completed.v1",
      deliberation_id: draft.id,
      frame_version: 1,
      role_key: "cfo",
      ...(await pinHashes(founderCtx, projectId, draft.id, "cfo")),
      descriptor: { conclusion: "Ok" },
    };

    await expect(
      recordExecutiveAnalysisCallback(
        founderCtx.workspaceId,
        projectId,
        draft.id,
        callbackPayload
      )
    ).rejects.toThrow(/terminal state 'CANCELLED'/);
  });

  it("rejects stale frame, overlay drift and deployment drift; conflicting replay does not overwrite", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Identity checks" });
    await frameDeliberation(founderCtx, projectId, draft.id, {
      question: "Identity safety?",
      roleKeys: ["cfo"],
    });
    const hashes = await pinHashes(founderCtx, projectId, draft.id, "cfo");
    const base = {
      kind: "executive.analysis.completed.v1",
      deliberation_id: draft.id,
      frame_version: 1,
      role_key: "cfo",
      descriptor: { run_id: "run-cfo-1", conclusion: "A", confidence: "HIGH" },
      ...hashes,
    };
    const call = (payload: typeof base) =>
      recordExecutiveAnalysisCallback(founderCtx.workspaceId, projectId, draft.id, payload);

    await expect(call({ ...base, frame_version: 2 })).rejects.toThrow(/Frame version mismatch/);
    await expect(call({ ...base, overlay_pin_hash: "0".repeat(64) })).rejects.toThrow(
      /EXECUTIVE_CALLBACK_OVERLAY_PIN_MISMATCH/
    );
    await expect(call({ ...base, deployment_pin_hash: "0".repeat(64) })).rejects.toThrow(
      /EXECUTIVE_CALLBACK_DEPLOYMENT_PIN_MISMATCH/
    );
    const { deployment_pin_hash: _d, ...noHash } = base;
    await expect(call(noHash as typeof base)).rejects.toThrow(/DEPLOYMENT_PIN_MISMATCH/);

    // Callback đúng được nhận; replay giống hệt idempotent; replay khác nội dung bị từ chối.
    const first = await call(base);
    expect((await call(base)).id).toBe(first.id);
    await expect(
      call({ ...base, descriptor: { ...base.descriptor, conclusion: "B" } })
    ).rejects.toThrow(/EXECUTIVE_CALLBACK_CONFLICT/);
    const details = await getDeliberation(founderCtx, projectId, draft.id);
    expect(details.analyses).toHaveLength(1);
    expect(details.analyses?.[0].descriptor.conclusion).toBe("A");
  });
});
