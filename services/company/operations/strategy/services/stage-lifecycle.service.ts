import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db } from "../../models/db";
import { identityWorkspaces } from "../../../shared/db/schema/identity";
import { stagePolicies, ventureStageTransitions, evidence } from "../../../shared/db/schema/strategy";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { buildVentureStageChangedEvent } from "../events/venture-stage-events";
import { evaluateGate, EvidenceItem } from "./gate-evaluation.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

export type VentureStage =
  | "S0_GENESIS"
  | "S1_PROBLEM_VALIDATION"
  | "S2_SOLUTION_VALIDATION"
  | "S3_MVP_BUILD"
  | "S4_PRODUCT_MARKET_FIT"
  | "S5_SCALE";

export const VENTURE_STAGES: readonly VentureStage[] = [
  "S0_GENESIS",
  "S1_PROBLEM_VALIDATION",
  "S2_SOLUTION_VALIDATION",
  "S3_MVP_BUILD",
  "S4_PRODUCT_MARKET_FIT",
  "S5_SCALE",
] as const;

export interface AssessResult {
  currentStage: VentureStage;
  recommendedStage: VentureStage;
  gatePassed: boolean;
  blockers: string[];
}

export interface TransitionParams {
  workspaceId: bigint;
  toStage: VentureStage;
  reason: string;
  actorMemberId?: bigint;
  override?: boolean;
}

export interface TransitionResult {
  fromStage: VentureStage;
  toStage: VentureStage;
  enteredAt: string;
  overrideApplied: boolean;
}

export async function assessVentureStage(workspaceId: bigint): Promise<AssessResult> {
  const [ws] = await db
    .select({
      id: identityWorkspaces.id,
      companyStage: identityWorkspaces.companyStage,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, workspaceId))
    .limit(1);

  if (!ws) {
    throw APIError.notFound("Workspace không tồn tại");
  }

  const currentStage = (ws.companyStage as VentureStage) || "S0_GENESIS";
  const currentIndex = VENTURE_STAGES.indexOf(currentStage);
  const validCurrentIndex = currentIndex >= 0 ? currentIndex : 0;
  const nextIndex = Math.min(validCurrentIndex + 1, VENTURE_STAGES.length - 1);
  const recommendedStage = VENTURE_STAGES[nextIndex];

  // Kiểm tra chính sách gate của nextStage
  const [policy] = await db
    .select()
    .from(stagePolicies)
    .where(
      and(
        eq(stagePolicies.workspaceId, workspaceId),
        eq(stagePolicies.stageKey, recommendedStage)
      )
    )
    .limit(1);

  if (!policy) {
    return {
      currentStage,
      recommendedStage,
      gatePassed: true,
      blockers: [],
    };
  }

  // Load evidence của workspace
  const rawEvidence = await db
    .select()
    .from(evidence)
    .where(eq(evidence.workspaceId, workspaceId));

  const evidenceItems: EvidenceItem[] = rawEvidence.map((e) => ({
    id: e.id,
    sourceType: e.sourceType,
    strength: e.strength,
    confidence: e.confidence,
    supportsOrRefutes: e.supportsOrRefutes,
  }));

  const gateResult = evaluateGate({
    policy: {
      stageKey: policy.stageKey,
      minimumEvidenceScore: policy.minimumEvidenceScore,
      requirements: policy.requirements,
      blockingRiskRules: policy.blockingRiskRules,
    },
    evidenceList: evidenceItems,
  });

  const gatePassed = gateResult.result === "passed";
  const blockers: string[] = [];
  if (!gatePassed) {
    blockers.push(gateResult.rationale || "Bằng chứng chưa đạt yêu cầu của gate");
  }

  return {
    currentStage,
    recommendedStage,
    gatePassed,
    blockers,
  };
}

export async function transitionVentureStage(p: TransitionParams): Promise<TransitionResult> {
  const [ws] = await db
    .select({
      id: identityWorkspaces.id,
      companyStage: identityWorkspaces.companyStage,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, p.workspaceId))
    .limit(1);

  if (!ws) {
    throw APIError.notFound("Workspace không tồn tại");
  }

  const currentStage = (ws.companyStage as VentureStage) || "S0_GENESIS";
  const currentIndex = VENTURE_STAGES.indexOf(currentStage);
  const toIndex = VENTURE_STAGES.indexOf(p.toStage);

  if (toIndex === -1) {
    throw APIError.invalidArgument(`Stage đích '${p.toStage}' không hợp lệ`);
  }

  if (toIndex > currentIndex + 1) {
    throw APIError.invalidArgument("Chỉ được phép tiến tối đa 1 bậc stage");
  }

  if (toIndex < currentIndex) {
    if (!p.reason || !p.reason.trim()) {
      throw APIError.invalidArgument("Lùi stage bắt buộc phải cung cấp lý do");
    }
  }

  if (toIndex === currentIndex + 1) {
    const assess = await assessVentureStage(p.workspaceId);
    if (!assess.gatePassed && !p.override) {
      throw APIError.failedPrecondition(
        `Gate chưa đạt để lên ${p.toStage}: ${assess.blockers.join("; ")}`
      );
    }
  }

  const now = new Date();
  const transitionId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx
      .update(identityWorkspaces)
      .set({
        companyStage: p.toStage,
        ventureStageEnteredAt: now,
        updatedAt: now,
      })
      .where(eq(identityWorkspaces.id, p.workspaceId));

    await tx.insert(ventureStageTransitions).values({
      id: transitionId,
      workspaceId: p.workspaceId,
      fromStage: currentStage,
      toStage: p.toStage,
      reason: p.reason,
      actorMemberId: p.actorMemberId || null,
      overrideFlag: !!p.override,
      decidedAt: now,
      createdAt: now,
    });

    const event = buildVentureStageChangedEvent({
      workspaceId: p.workspaceId.toString(),
      fromStage: currentStage,
      toStage: p.toStage,
      reason: p.reason,
      overrideFlag: !!p.override,
      actorMemberId: p.actorMemberId ? p.actorMemberId.toString() : null,
    });
    await appendOutboxEvent(tx, event);
  });

  return {
    fromStage: currentStage,
    toStage: p.toStage,
    enteredAt: now.toISOString(),
    overrideApplied: !!p.override,
  };
}

export async function listVentureStageTransitions(workspaceId: bigint) {
  return db
    .select()
    .from(ventureStageTransitions)
    .where(eq(ventureStageTransitions.workspaceId, workspaceId))
    .orderBy(desc(ventureStageTransitions.decidedAt));
}
