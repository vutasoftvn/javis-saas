// services/company/operations/strategy/tests/strategy-workflow-e2e.test.ts
//
// Task 12: End-to-end governance contract test.
//
// Two workspaces, four actor roles:
//   Founder           — highest authority, FOUNDER_ONLY policy holder
//   Delegated approver — member with delegated strategy.initiative.approve role
//   Regular member     — can read/write evidence, cannot approve
//   Strategy agent     — AI actor, blocked from governance transitions
//
// Happy path covers:
//   settings → strategic objective → BSC scope → PESTEL signal → resource
//   assessment → SWOT → TOWS score/select → OKR Cycle/Objective/KRs/publish
//   → Initiative/approve → task (with APPROVED initiative) → 12-week cycle
//   → weekly plan/commitment → cycle reviews (mid-cycle auto-scheduled, close
//   END_CYCLE with governance).
//
// Negative paths:
//   1. BSC REQUIRED blocks PESTEL when no matching active scope perspective
//   2. Cross-workspace TOWS not found in different workspace
//   3. Publishing Objective with > 3 KRs rejected
//   4. Agent cannot select TOWS (selectTowsOption rejects agent callers)
//   5. Unapproved (DRAFT) Initiative blocked from task linkage
//   6. END_CYCLE review close by regular member rejected under FOUNDER_ONLY
//   7. Founder retains approve authority under DELEGATED_APPROVER policy
//   8. All parent IDs and settingsRevision preserved in lineage
//
import { describe, it, expect } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
} from "../../tests/_helpers";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  updateWorkspaceStrategySettings,
} from "../services/workspace-strategy-settings.service";
import {
  createStrategicObjective,
  saveBscFocusScopes,
} from "../services/strategic-objective.service";
import {
  createPestelSignal,
  createResourceCapabilityAssessment,
  createSwotItem,
} from "../services/strategy-analysis.service";
import {
  createTowsOption,
  createTowsOptionEvaluation,
  selectTowsOption,
} from "../services/tows-option.service";
import {
  createOkrCycleService,
  createObjectiveService,
  addKeyResultService,
  publishObjectiveService,
} from "../../services/okr.service";
import {
  createInitiativeService,
  approveInitiativeService,
} from "../../services/initiative.service";
import {
  createTaskService,
} from "../../services/task.service";
import {
  createCycleService,
  createWeeklyPlanService,
  createWeeklyCommitmentService,
} from "../../services/twelve-week-year.service";
import {
  listCycleReviewsService,
  startCycleReviewService,
  closeCycleReviewService,
} from "../services/cycle-review.service";
import {
  requireStrategyGovernanceAuthority,
} from "../services/strategy-governance-authorization.service";

// ────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────

function makeTenantCtx(
  workspaceId: string,
  userId: string,
  role: string,
  extra: Partial<TenantContext> = {}
): TenantContext {
  return {
    workspaceId,
    userId,
    membershipRole: role,
    permissions: role === "founder" ? ["*"] : [],
    correlationId: `e2e-${Date.now()}`,
    ...extra,
  } as TenantContext;
}

function makeAgentCtx(workspaceId: string, userId: string): TenantContext {
  return {
    workspaceId,
    userId,
    membershipRole: "agent",
    permissions: [],
    correlationId: "e2e-agent",
    actorKind: "AI_AGENT",
    isAgent: true,
  } as any;
}

// ────────────────────────────────────────────────────────────────────────────
// E2E Tests
// ────────────────────────────────────────────────────────────────────────────

describe("Task 12: Strategy Workflow E2E Governance Contract", () => {

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Full happy path
  // ──────────────────────────────────────────────────────────────────────────

  describe("1. Happy path: settings → TOWS → OKR → Initiative → execution → review", () => {
    it("Founder drives full governance lineage end-to-end", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");
      const auth = ws.bearerToken;

      // ── Settings ──────────────────────────────────────────────────────────
      const settings = await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        bscMode: "OPTIONAL",
        approvalPolicy: "FOUNDER_ONLY",
        towsSelectionLimit: 2,
        expectedRevision: 1,
      });
      expect(settings.bscMode).toBe("OPTIONAL");
      expect(settings.approvalPolicy).toBe("FOUNDER_ONLY");
      expect(settings.revision).toBe(1);

      // ── Strategic Objective (ACTIVE with successDefinition) ──────────────
      const soActive = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Trở thành nền tảng SaaS số 1 Đông Nam Á",
        status: "ACTIVE",
        successDefinition: "Đạt 500 khách hàng doanh nghiệp trả phí",
      });
      expect(soActive.status).toBe("ACTIVE");
      expect(soActive.workspaceId).toBe(ws.workspaceId);

      // ── BSC scope ─────────────────────────────────────────────────────
      const scopes = await saveBscFocusScopes(founderCtx, {
        workspaceId: ws.workspaceId,
        strategicObjectiveId: soActive.id,
        scopes: [
          {
            perspective: "CUSTOMER",
            focusStatement: "Tập trung vào trải nghiệm khách hàng Q4",
            status: "ACTIVE",
          },
        ],
      });
      expect(scopes.length).toBe(1);
      expect(scopes[0].perspective).toBe("CUSTOMER");

      // ── PESTEL signal ─────────────────────────────────────────────────────
      const pestelSignal = await createPestelSignal(founderCtx, {
        strategicObjectiveId: soActive.id,
        dimension: "TECHNOLOGICAL",
        statement: "Tốc độ AI adoption ở Đông Nam Á tăng mạnh",
        impact: "POSITIVE",
        certainty: "HIGH",
      });
      expect(pestelSignal.id).toBeDefined();
      expect(pestelSignal.strategicObjectiveId).toBe(soActive.id);

      // ── Resource & Capability Assessment ─────────────────────────────────────────
      const resource = await createResourceCapabilityAssessment(founderCtx, {
        strategicObjectiveId: soActive.id,
        category: "TECHNOLOGY_OPERATIONAL_ASSET",
        statement: "Kiến trúc microservice đang cho phép scale nhanh",
        strengthLevel: "STRONG",
      });
      expect(resource.id).toBeDefined();

      // ── SWOT items ────────────────────────────────────────────────────────
      const swotS = await createSwotItem(founderCtx, {
        strategicObjectiveId: soActive.id,
        kind: "STRENGTH",
        statement: "Engineering team với 40+ senior devs",
        sourceType: "MANUAL",
        status: "ACTIVE",
      });
      expect(swotS.kind).toBe("STRENGTH");

      const swotT = await createSwotItem(founderCtx, {
        strategicObjectiveId: soActive.id,
        kind: "THREAT",
        statement: "Cạnh tranh từ BigTech có nguồn lực lớn",
        sourceType: "MANUAL",
        status: "ACTIVE",
      });
      expect(swotT.id).toBeDefined();

      // ── TOWS option: ST strategy ──────────────────────────────────────────
      const towsOpt = await createTowsOption({
        workspaceId: ws.workspaceId,
        strategicObjectiveId: soActive.id,
        quadrant: "ST",
        title: "Tận dụng kỹ thuật để đối đầu BigTech",
        swotItemIds: [swotS.id, swotT.id],
      });
      expect(towsOpt.id).toBeDefined();
      expect(towsOpt.status).toBe("DRAFT");

      // Score TOWS (impactScore 1..5, difficultyScore 1..5)
      await createTowsOptionEvaluation({
        workspaceId: ws.workspaceId,
        towsOptionId: towsOpt.id,
        impactScore: 5,
        difficultyScore: 2,
      });

      // Select TOWS (human transition — requires governance authority)
      const selectedTows = await selectTowsOption({ id: towsOpt.id }, founderCtx);
      expect(selectedTows.status).toBe("SELECTED");
      expect(selectedTows.decisionId).toBeDefined();

      // ── OKR Cycle ─────────────────────────────────────────────────────────
      const okrCycle = await createOkrCycleService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        name: "2026-Q4",
      });
      expect(okrCycle.id).toBeDefined();

      // ── Objective (from TOWS) ─────────────────────────────────────────────
      const objective = await createObjectiveService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        cycleId: okrCycle.id,
        title: "Đạt 50 khách hàng doanh nghiệp ký SLA",
        towsOptionId: towsOpt.id,
        strategicObjectiveId: soActive.id,
      });
      expect(objective.towsOptionId).toBe(towsOpt.id);
      expect(objective.strategicObjectiveId).toBe(soActive.id);
      expect(objective.cycleId).toBe(okrCycle.id);

      // ── Key Results (max 3) ───────────────────────────────────────────────
      const kr1 = await addKeyResultService({
        objectiveId: objective.id,
        authorization: auth,
        title: "50 enterprise contracts signed",
        targetValue: 50,
        baselineValue: 0,
        unit: "contracts",
      });
      const kr2 = await addKeyResultService({
        objectiveId: objective.id,
        authorization: auth,
        title: "NPS ≥ 70",
        targetValue: 70,
        baselineValue: 0,
        unit: "NPS",
      });
      const kr3 = await addKeyResultService({
        objectiveId: objective.id,
        authorization: auth,
        title: "ARR tăng 3x so với Q3",
        targetValue: 3,
        baselineValue: 0,
        unit: "x",
      });
      expect(kr1.objectiveId).toBe(objective.id);
      expect(kr2.objectiveId).toBe(objective.id);
      expect(kr3.objectiveId).toBe(objective.id);

      // ── Publish OKR (requires strategy.okr.publish authority) ────────────
      const published = await publishObjectiveService({ id: objective.id }, founderCtx);
      expect(published.status).toBe("published");

      // ── Initiative ────────────────────────────────────────────────────────
      const initiative = await createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          title: "Enterprise Go-to-Market Sprint",
          strategicObjectiveId: soActive.id,
        },
        auth
      );
      expect(initiative.approvalStatus).toBe("DRAFT");

      // Verify requireStrategyGovernanceAuthority allows founder
      const govDecision = await requireStrategyGovernanceAuthority(
        founderCtx,
        "strategy.initiative.approve"
      );
      expect(govDecision.effect).toBe("ALLOW");

      // ── Approve Initiative ────────────────────────────────────────────────
      const approved = await approveInitiativeService(
        { id: initiative.id, reason: "Đã review, hợp với OKR Q4" },
        founderCtx
      );
      expect(approved.approvalStatus).toBe("APPROVED");
      expect(approved.decisionId).toBeDefined();
      // Policy revision snapshotted at approval time
      expect(approved.settingsRevision).toBe(settings.revision);

      // ── Task linked to APPROVED Initiative ───────────────────────────────
      const task = await createTaskService(
        {
          workspaceId: ws.workspaceId,
          title: "Gọi điện cho 10 prospect tuần này",
          initiativeId: initiative.id,
        },
        auth
      );
      expect(task.initiativeId).toBe(initiative.id);

      // ── 10-week Execution Cycle ───────────────────────────────────────────
      const execCycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        visionStatement: "Chinh phục thị trường enterprise Đông Nam Á",
        durationWeeks: 10,
      });
      expect(execCycle.durationWeeks).toBe(10);

      // Mid-cycle review auto-scheduled at week 5 (ceil(10/2))
      const reviews = await listCycleReviewsService(
        BigInt(ws.workspaceId),
        BigInt(execCycle.id)
      );
      const midReview = reviews.find((r) => r.kind === "MID_CYCLE");
      expect(midReview).toBeDefined();
      expect(midReview!.scheduledWeekNo).toBe(5);
      expect(midReview!.status).toBe("SCHEDULED");

      // END_CYCLE review exists
      const endReview = reviews.find((r) => r.kind === "END_CYCLE");
      expect(endReview).toBeDefined();
      expect(endReview!.scheduledWeekNo).toBe(10);

      // ── Weekly Plan + Commitment ──────────────────────────────────────────
      const wPlan = await createWeeklyPlanService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        cycleId: execCycle.id,
        weekNo: 1,
        focus: "Pipeline building",
      });
      expect(wPlan.cycleId).toBe(execCycle.id);

      const commitment = await createWeeklyCommitmentService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        weeklyPlanId: wPlan.id,
        initiativeId: initiative.id,
        title: "Hoàn thành 10 cuộc gọi khách hàng",
        plannedEffort: "MEDIUM",
      });
      expect(commitment.initiativeId).toBe(initiative.id);

      // ── Start + Close END_CYCLE review (requires governance) ─────────────
      const started = await startCycleReviewService(founderCtx, BigInt(endReview!.id));
      expect(started.status).toBe("IN_PROGRESS");

      const closed = await closeCycleReviewService(founderCtx, BigInt(endReview!.id), {
        conclusion: "All Q4 objectives met",
      });
      expect(closed.status).toBe("COMPLETED");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. BSC REQUIRED blocks PESTEL when no active scope perspective
  // ──────────────────────────────────────────────────────────────────────────

  describe("2. Negative: BSC REQUIRED blocks PESTEL with no matching scope perspective", () => {
    it("rejects createPestelSignal when BSC REQUIRED and perspective has no active scope", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");

      // Create ACTIVE SO FIRST (before setting BSC REQUIRED, so no scope needed for activation)
      const so = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Mở rộng sang thị trường B2C",
        status: "ACTIVE",
        successDefinition: "50K MAU",
      });

      // NOW set BSC REQUIRED with CUSTOMER perspective enabled
      // BSC REQUIRED requires enabledBscPerspectives to be non-empty
      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        bscMode: "REQUIRED",
        enabledBscPerspectives: ["CUSTOMER"],
        expectedRevision: 1,
      });

      // No BSC scopes created for this SO → activeScopesSet is empty
      // PESTEL with CUSTOMER perspective should be rejected (empty intersection)
      await expect(
        createPestelSignal(founderCtx, {
          strategicObjectiveId: so.id,
          dimension: "ECONOMIC",
          statement: "Test signal without BSC scope",
          impact: "POSITIVE",
          certainty: "MEDIUM",
          bscPerspectives: ["CUSTOMER"], // CUSTOMER enabled but no active scope for this SO
        })
      ).rejects.toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Cross-workspace data rejected
  // ──────────────────────────────────────────────────────────────────────────

  describe("3. Negative: cross-workspace data rejected", () => {
    it("cannot select TOWS option from workspace B using workspace A context", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "founder" });
      const wsB = await createTestWorkspaceWithMember({ role: "founder" });
      const ctxA = makeTenantCtx(wsA.workspaceId, wsA.userId, "founder");
      const ctxB = makeTenantCtx(wsB.workspaceId, wsB.userId, "founder");

      // Create SO + TOWS in workspace B
      const soB = await createStrategicObjective(ctxB, {
        workspaceId: wsB.workspaceId,
        title: "Objective in workspace B",
        status: "DRAFT",
      });
      const towsB = await createTowsOption({
        workspaceId: wsB.workspaceId,
        strategicObjectiveId: soB.id,
        quadrant: "SO",
        title: "WsB TOWS option",
        swotItemIds: [],
      });
      await createTowsOptionEvaluation({
        workspaceId: wsB.workspaceId,
        towsOptionId: towsB.id,
        impactScore: 3,
        difficultyScore: 3,
      });

      // Attempt to select towsB from workspace A context — should fail (not found in wsA)
      await expect(
        selectTowsOption({ id: towsB.id }, ctxA)
      ).rejects.toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. A fourth Key Result is rejected
  // ──────────────────────────────────────────────────────────────────────────

  describe("4. Negative: a fourth Key Result is rejected", () => {
    it("rejects addKeyResultService once an objective already has 3 KRs", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const auth = ws.bearerToken;

      const okrCycle = await createOkrCycleService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        name: "4KR-test-cycle",
      });
      const objective = await createObjectiveService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        cycleId: okrCycle.id,
        title: "Test 4-KR limit",
      });

      for (let i = 1; i <= 3; i++) {
        await addKeyResultService({
          objectiveId: objective.id,
          authorization: auth,
          title: `KR ${i}`,
          targetValue: i * 10,
          unit: "units",
        });
      }

      await expect(
        addKeyResultService({
          objectiveId: objective.id,
          authorization: auth,
          title: "KR 4",
          targetValue: 40,
          unit: "units",
        })
      ).rejects.toThrow("maximum of 3 Key Results");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Agent cannot select TOWS (human-in-the-loop)
  // ──────────────────────────────────────────────────────────────────────────

  describe("5. Negative: agent cannot auto-select TOWS", () => {
    it("rejects selectTowsOption when caller is an AI agent", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");
      const agentCtx = makeAgentCtx(ws.workspaceId, ws.userId);

      const so = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Agent TOWS test SO",
        status: "ACTIVE",
        successDefinition: "Human selects one evaluated strategy",
      });
      const swot = await createSwotItem(founderCtx, {
        strategicObjectiveId: so.id,
        kind: "STRENGTH",
        statement: "Human-reviewed strategy input",
        sourceType: "MANUAL",
        status: "ACTIVE",
      });
      const towsOpt = await createTowsOption({
        workspaceId: ws.workspaceId,
        strategicObjectiveId: so.id,
        quadrant: "SO",
        title: "Agent proposal",
        swotItemIds: [swot.id],
      });
      await createTowsOptionEvaluation({
        workspaceId: ws.workspaceId,
        towsOptionId: towsOpt.id,
        impactScore: 3,
        difficultyScore: 2,
      });

      // Agent actor must be rejected at governance gate
      await expect(
        selectTowsOption({ id: towsOpt.id }, agentCtx)
      ).rejects.toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. DRAFT Initiative blocked from task linkage
  // ──────────────────────────────────────────────────────────────────────────

  describe("6. Negative: DRAFT Initiative rejected as task initiative_id", () => {
    it("rejects createTask when linked Initiative is still DRAFT", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const auth = ws.bearerToken;

      const initiative = await createInitiativeService(
        { workspaceId: ws.workspaceId, title: "Unapproved draft initiative" },
        auth
      );
      expect(initiative.approvalStatus).toBe("DRAFT");

      await expect(
        createTaskService(
          {
            workspaceId: ws.workspaceId,
            title: "Task with unapproved initiative",
            initiativeId: initiative.id,
          },
          auth
        )
      ).rejects.toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 7. END_CYCLE review close by regular member rejected
  // ──────────────────────────────────────────────────────────────────────────

  describe("7. Negative: END_CYCLE review close by non-founder rejected", () => {
    it("rejects closeCycleReviewService for END_CYCLE when actor is regular member", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");
      const auth = ws.bearerToken;

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        approvalPolicy: "FOUNDER_ONLY",
        expectedRevision: 1,
      });

      const execCycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        visionStatement: "Test governance on review close",
        durationWeeks: 4,
      });

      const reviews = await listCycleReviewsService(
        BigInt(ws.workspaceId),
        BigInt(execCycle.id)
      );
      const endReview = reviews.find((r) => r.kind === "END_CYCLE");
      expect(endReview).toBeDefined();

      // Start it first so status becomes IN_PROGRESS
      await startCycleReviewService(founderCtx, BigInt(endReview!.id));

      // Regular member tries to close END_CYCLE review — blocked by governance
      const memberInfo = await addMemberToWorkspace(ws.workspaceId, "member");
      const memberCtx = makeTenantCtx(ws.workspaceId, memberInfo.userId, "member");

      await expect(
        closeCycleReviewService(memberCtx, BigInt(endReview!.id), {
          conclusion: "Attempted by non-founder",
        })
      ).rejects.toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 8. DELEGATED_APPROVER: founder retains approve authority
  // ──────────────────────────────────────────────────────────────────────────

  describe("8. DELEGATED_APPROVER policy: founder retains approve authority", () => {
    it("founder can approve Initiative under DELEGATED_APPROVER policy", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");
      const auth = ws.bearerToken;

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        approvalPolicy: "DELEGATED_APPROVER",
        expectedRevision: 1,
      });

      const initiative = await createInitiativeService(
        { workspaceId: ws.workspaceId, title: "Delegated approval test" },
        auth
      );
      expect(initiative.approvalStatus).toBe("DRAFT");

      const approved = await approveInitiativeService(
        { id: initiative.id, reason: "Approved by founder under DELEGATED_APPROVER" },
        founderCtx
      );
      expect(approved.approvalStatus).toBe("APPROVED");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 9. Lineage: all parent IDs and settingsRevision preserved
  // ──────────────────────────────────────────────────────────────────────────

  describe("9. Lineage: all parent IDs and policy revision preserved", () => {
    it("OKR Objective has towsOptionId + strategicObjectiveId; approved Initiative settingsRevision matches settings", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantCtx(ws.workspaceId, ws.userId, "founder");
      const auth = ws.bearerToken;

      const settings = await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        expectedRevision: 1,
      });

      const so = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Lineage test SO",
        status: "ACTIVE",
        successDefinition: "Preserve complete strategic lineage",
      });
      const swot = await createSwotItem(founderCtx, {
        strategicObjectiveId: so.id,
        kind: "WEAKNESS",
        statement: "Lineage SWOT source",
        sourceType: "MANUAL",
        status: "ACTIVE",
      });

      const towsOpt = await createTowsOption({
        workspaceId: ws.workspaceId,
        strategicObjectiveId: so.id,
        quadrant: "WT",
        title: "Lineage TOWS",
        swotItemIds: [swot.id],
      });
      await createTowsOptionEvaluation({
        workspaceId: ws.workspaceId,
        towsOptionId: towsOpt.id,
        impactScore: 3,
        difficultyScore: 2,
      });
      await selectTowsOption({ id: towsOpt.id }, founderCtx);

      const okrCycle = await createOkrCycleService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        name: "Lineage Q4",
      });

      const objective = await createObjectiveService({
        workspaceId: ws.workspaceId,
        authorization: auth,
        cycleId: okrCycle.id,
        title: "Lineage objective",
        strategicObjectiveId: so.id,
        towsOptionId: towsOpt.id,
      });

      // All parent IDs must be preserved
      expect(objective.cycleId).toBe(okrCycle.id);
      expect(objective.strategicObjectiveId).toBe(so.id);
      expect(objective.towsOptionId).toBe(towsOpt.id);

      const kr = await addKeyResultService({
        objectiveId: objective.id,
        authorization: auth,
        title: "Lineage KR",
        targetValue: 100,
        unit: "%",
      });
      expect(kr.objectiveId).toBe(objective.id);

      const initiative = await createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          title: "Lineage initiative",
          strategicObjectiveId: so.id,
        },
        auth
      );
      const approvedInitiative = await approveInitiativeService(
        { id: initiative.id },
        founderCtx
      );

      // Policy revision snapshot must match settings.revision
      expect(approvedInitiative.settingsRevision).toBe(settings.revision);
      expect(approvedInitiative.decisionId).toBeDefined();
    });
  });
});
