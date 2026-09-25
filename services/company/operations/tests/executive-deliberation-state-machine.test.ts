import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  createTestWorkspaceWithMember,
  makeTestTenantContext,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  appendFounderDecision,
  cancelDeliberation,
  createDraftDeliberation,
  frameDeliberation,
  getDeliberation,
  getDeliberationAuthority,
  recordExecutiveAnalysisCallback,
} from "../services/executive-deliberation.service";
import {
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";
import { computeDeploymentPinHash, computeOverlayPinHash } from "../services/executive-pin-hash";
import type { SelectedAdvisorExecutionPin } from "../services/executive-deliberation.service";

// COSA Control Plane là app khác — giả lập đúng catalog generated.
vi.mock("../services/advisor-overlay.client", () => ({
  fetchAdvisorOverlayIdentity: vi.fn(async (_ws: string, roleKey: string) => {
    const { ADVISOR_OVERLAY_CATALOG: catalog } = await import(
      "../../shared/contracts/executive-advisor-overlays.generated"
    );
    return catalog[roleKey];
  }),
}));

/**
 * Vòng đời Deliberation sau khi advisor chạy: retry worker idempotent, role bị
 * tắt giữa chừng không làm kẹt, trạng thái cuối phản ánh đúng kết quả, và
 * quyết định Founder chỉ xảy ra khi đã có phân tích.
 */
describe("Executive Deliberation state machine", () => {
  let founderCtx: TenantContext;
  let projectId: string;

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
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "marketing");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
  });

  async function framed(roleKeys: string[]): Promise<string> {
    const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Pricing" });
    await frameDeliberation(founderCtx, projectId, draft.id, {
      question: "Should we raise prices?",
      roleKeys,
    });
    return draft.id;
  }

  async function callback(
    delibId: string,
    roleKey: string,
    kind: "completed" | "failed",
    frameVersion = 1
  ) {
    const details = await getDeliberation(founderCtx, projectId, delibId);
    const pin = (details.activeFrame?.selectedRoles as SelectedAdvisorExecutionPin[]).find(
      (r) => r.roleKey === roleKey
    )!;
    const base = {
      deliberation_id: delibId,
      frame_version: frameVersion,
      role_key: roleKey,
      deployment_pin_hash: computeDeploymentPinHash(pin.deployment),
      overlay_pin_hash: computeOverlayPinHash(pin.overlay),
    };
    const payload =
      kind === "completed"
        ? {
            ...base,
            kind: "executive.analysis.completed.v1",
            descriptor: { run_id: `run-${roleKey}-${frameVersion}`, conclusion: "ok", evidence_claims: [] },
          }
        : { ...base, kind: "executive.analysis.failed.v1", error_detail: "AUTHORITY_DENIED: paused" };
    return recordExecutiveAnalysisCallback(founderCtx.workspaceId, projectId, delibId, payload);
  }

  describe("worker retry idempotency (authority existingAnalysis)", () => {
    it("reports existingAnalysis only for the role already recorded in the active frame", async () => {
      const delibId = await framed(["cfo", "cmo"]);
      await callback(delibId, "cfo", "completed");

      const cfo = await getDeliberationAuthority(founderCtx.workspaceId, projectId, delibId, "cfo", 1);
      const cmo = await getDeliberationAuthority(founderCtx.workspaceId, projectId, delibId, "cmo", 1);

      expect(cfo.existingAnalysis).toEqual({ status: "COMPLETED" });
      expect(cmo.existingAnalysis).toBeNull();
    });

    it("recorded role stays readable for retry even after its office is disabled", async () => {
      const delibId = await framed(["cfo", "cmo"]);
      await callback(delibId, "cfo", "completed");
      await disableWorkspaceExecutiveRole(founderCtx, "cfo", { reason: "pause" });

      const cfo = await getDeliberationAuthority(founderCtx.workspaceId, projectId, delibId, "cfo", 1);
      expect(cfo.existingAnalysis).toEqual({ status: "COMPLETED" });
    });
  });

  describe("office disabled mid-analysis", () => {
    it("records a FAILED outcome so the deliberation can converge", async () => {
      const delibId = await framed(["cfo"]);
      await disableWorkspaceExecutiveRole(founderCtx, "cfo", { reason: "pause" });

      const res = await callback(delibId, "cfo", "failed");

      expect(res.status).toBe("FAILED");
    });

    it("still rejects a COMPLETED analysis from a disabled office", async () => {
      const delibId = await framed(["cfo"]);
      await disableWorkspaceExecutiveRole(founderCtx, "cfo", { reason: "pause" });

      await expect(callback(delibId, "cfo", "completed")).rejects.toThrow(/disabled or revoked/);
    });
  });

  describe("terminal analysis state", () => {
    it("all roles FAILED -> FAILED_REQUIRES_ATTENTION", async () => {
      const delibId = await framed(["cfo", "cmo"]);
      await callback(delibId, "cfo", "failed");
      await callback(delibId, "cmo", "failed");

      const d = await getDeliberation(founderCtx, projectId, delibId);
      expect(d.state).toBe("FAILED_REQUIRES_ATTENTION");
    });

    it("partial success -> AWAITING_FOUNDER", async () => {
      const delibId = await framed(["cfo", "cmo"]);
      await callback(delibId, "cfo", "completed");
      await callback(delibId, "cmo", "failed");

      const d = await getDeliberation(founderCtx, projectId, delibId);
      expect(d.state).toBe("AWAITING_FOUNDER");
    });

    it("FAILED_REQUIRES_ATTENTION can be re-framed with a new frame version", async () => {
      const delibId = await framed(["cfo"]);
      await callback(delibId, "cfo", "failed");

      const reframed = await frameDeliberation(founderCtx, projectId, delibId, {
        question: "Retry with fresh evidence",
        roleKeys: ["cfo"],
      });

      expect(reframed.state).toBe("ANALYSIS_QUEUED");
      expect(reframed.activeFrameVersion).toBe(2);
    });

    it("FAILED_REQUIRES_ATTENTION can be cancelled", async () => {
      const delibId = await framed(["cfo"]);
      await callback(delibId, "cfo", "failed");

      const res = await cancelDeliberation(founderCtx, projectId, delibId, { reason: "drop" });
      expect(res.state).toBe("CANCELLED");
    });
  });

  describe("critic review (no critic runner)", () => {
    it("rejects criticRequired at frame time before writing anything", async () => {
      const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Critic" });

      await expect(
        frameDeliberation(founderCtx, projectId, draft.id, {
          question: "Needs critic?",
          roleKeys: ["cfo"],
          criticRequired: true,
        })
      ).rejects.toThrow(/CRITIC_REVIEW_NOT_AVAILABLE/);

      const d = await getDeliberation(founderCtx, projectId, draft.id);
      expect(d.state).toBe("DRAFT");
      expect(d.activeFrameVersion).toBe(0);
    });
  });

  describe("founder decision guard", () => {
    it("rejects APPROVE before analyses are complete", async () => {
      const delibId = await framed(["cfo", "cmo"]);

      await expect(
        appendFounderDecision(founderCtx, projectId, delibId, { decisionType: "APPROVE" })
      ).rejects.toThrow(/DELIBERATION_NOT_AWAITING_FOUNDER/);

      await callback(delibId, "cfo", "completed");
      await expect(
        appendFounderDecision(founderCtx, projectId, delibId, { decisionType: "REJECT" })
      ).rejects.toThrow(/DELIBERATION_NOT_AWAITING_FOUNDER/);
    });

    it("rejects APPROVE on a draft", async () => {
      const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Draft only" });
      await expect(
        appendFounderDecision(founderCtx, projectId, draft.id, { decisionType: "APPROVE" })
      ).rejects.toThrow(/DELIBERATION_NOT_AWAITING_FOUNDER/);
    });

    it("accepts APPROVE once AWAITING_FOUNDER", async () => {
      const delibId = await framed(["cfo"]);
      await callback(delibId, "cfo", "completed");

      const decision = await appendFounderDecision(founderCtx, projectId, delibId, {
        decisionType: "APPROVE",
      });
      expect(decision.decisionType).toBe("APPROVE");
      const d = await getDeliberation(founderCtx, projectId, delibId);
      expect(d.state).toBe("DECIDED");
    });

    it("allows CANCEL decision while analysis is still running", async () => {
      const delibId = await framed(["cfo", "cmo"]);
      await callback(delibId, "cfo", "completed");

      const decision = await appendFounderDecision(founderCtx, projectId, delibId, {
        decisionType: "CANCEL",
      });
      expect(decision.decisionType).toBe("CANCEL");
    });
  });
});
