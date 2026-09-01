import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db } from "../../models/db";
import { identityWorkspaces } from "../../../shared/db/schema/identity";
import { stagePolicies, stageTransitionPolicies, workspaceStageTransitions, evidence } from "../../../shared/db/schema/strategy";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { buildVentureStageChangedEvent } from "../events/venture-stage-events";
import { evaluateGate, EvidenceItem, parseStagePolicyRules } from "./gate-evaluation.service";
import { toJsonArray } from "./strategy-json";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

// M4 §1 — Workspace lifecycle stage (W0..W5), độc lập với Project stage (P0..P6).
// Giữ alias `VentureStage` cho tương thích import cũ trong cùng phiên rename.
export type WorkspaceLifecycleStage =
  | "W0_IDEA"
  | "W1_PROBLEM_VALIDATION"
  | "W2_SOLUTION_VALIDATION"
  | "W3_MVP_BUILD"
  | "W4_PRODUCT_MARKET_FIT"
  | "W5_SCALE";
export type VentureStage = WorkspaceLifecycleStage;

export const WORKSPACE_LIFECYCLE_STAGES: readonly WorkspaceLifecycleStage[] = [
  "W0_IDEA",
  "W1_PROBLEM_VALIDATION",
  "W2_SOLUTION_VALIDATION",
  "W3_MVP_BUILD",
  "W4_PRODUCT_MARKET_FIT",
  "W5_SCALE",
] as const;
export const VENTURE_STAGES = WORKSPACE_LIFECYCLE_STAGES;

// M1 §7 — chỉ các role này mới được chuyển stage khi thiếu policy / override gate.
const PRIVILEGED_ROLES = new Set(["founder", "co-founder", "admin"]);

export interface AssessResult {
  currentStage: VentureStage;
  recommendedStage: VentureStage;
  gatePassed: boolean;
  blockers: string[];
  // true khi workspace chưa cấu hình stage transition policy cho recommendedStage.
  // Fail-closed: KHÔNG suy ra gatePassed=true từ việc thiếu policy.
  policyMissing: boolean;
  // M4 §2 — version của policy đã đánh giá (ghi vào journal), số evidence item xét tới.
  policyVersion?: string;
  evidenceCount?: number;
}

export interface TransitionParams {
  workspaceId: bigint;
  toStage: VentureStage;
  reason: string;
  actorMemberId?: bigint;
  // Role membership của caller (ctx.membershipRole). Bắt buộc để override / đi tiếp khi thiếu policy.
  actorRole?: string;
  // true khi caller là agent/automation (không phải người bấm nút).
  isAutonomous?: boolean;
  override?: boolean;
  // M4 §2 — nguồn phát sinh transition + ref của approval khi override.
  source?: "manual" | "autonomous" | "api" | "system";
  overrideApprovalRef?: string;
}

export interface TransitionResult {
  fromStage: VentureStage;
  toStage: VentureStage;
  enteredAt: string;
  overrideApplied: boolean;
  // M4 §2 — true khi request cùng stage hiện tại (no-op, KHÔNG ghi history row).
  noop: boolean;
  // stage_version sau transition (đã +1 khi có thay đổi thật).
  stageVersion: number;
}

export async function assessVentureStage(workspaceId: bigint): Promise<AssessResult> {
  const [ws] = await db
    .select({
      id: identityWorkspaces.id,
      lifecycleStage: identityWorkspaces.lifecycleStage,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, workspaceId))
    .limit(1);

  if (!ws) {
    throw APIError.notFound("Workspace không tồn tại");
  }

  const currentStage = (ws.lifecycleStage as WorkspaceLifecycleStage) || "W0_IDEA";
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
    // Fail-closed: không có policy ⇒ không khẳng định gate đã đạt.
    return {
      currentStage,
      recommendedStage,
      gatePassed: false,
      blockers: [
        `Chưa cấu hình stage transition policy cho ${recommendedStage} — fail-closed`,
      ],
      policyMissing: true,
      evidenceCount: 0,
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

  const parsedRequirements = parseStagePolicyRules(policy.requirements);
  const gateResult = evaluateGate({
    policy: {
      stageKey: policy.stageKey,
      minimumEvidenceScore: policy.minimumEvidenceScore,
      requirements: parsedRequirements.rules,
      blockingRiskRules: toJsonArray(policy.blockingRiskRules),
      invalidRequirementCount: parsedRequirements.invalidCount,
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
    policyMissing: false,
    evidenceCount: evidenceItems.length,
  };
}

export async function transitionVentureStage(p: TransitionParams): Promise<TransitionResult> {
  const [ws] = await db
    .select({
      id: identityWorkspaces.id,
      lifecycleStage: identityWorkspaces.lifecycleStage,
      stageVersion: identityWorkspaces.stageVersion,
      stageEnteredAt: identityWorkspaces.stageEnteredAt,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, p.workspaceId))
    .limit(1);

  if (!ws) {
    throw APIError.notFound("Workspace không tồn tại");
  }

  const currentStage = (ws.lifecycleStage as WorkspaceLifecycleStage) || "W0_IDEA";
  const currentIndex = VENTURE_STAGES.indexOf(currentStage);
  const toIndex = VENTURE_STAGES.indexOf(p.toStage);

  if (toIndex === -1) {
    throw APIError.invalidArgument(`Stage đích '${p.toStage}' không hợp lệ`);
  }

  // M4 §2 — same-stage request là no-op tường minh: KHÔNG ghi history row giả.
  if (toIndex === currentIndex) {
    return {
      fromStage: currentStage,
      toStage: p.toStage,
      enteredAt: (ws.stageEnteredAt ?? new Date()).toISOString(),
      overrideApplied: false,
      noop: true,
      stageVersion: ws.stageVersion,
    };
  }

  if (toIndex > currentIndex + 1) {
    throw APIError.invalidArgument("Chỉ được phép tiến tối đa 1 bậc stage");
  }

  if (toIndex < currentIndex) {
    if (!p.reason || !p.reason.trim()) {
      throw APIError.invalidArgument("Lùi stage bắt buộc phải cung cấp lý do");
    }
  }

  let assessResult: AssessResult | null = null;

  if (toIndex === currentIndex + 1) {
    const assess = await assessVentureStage(p.workspaceId);
    assessResult = assess;
    const privileged = !!p.actorRole && PRIVILEGED_ROLES.has(p.actorRole);

    if (assess.policyMissing) {
      // M1 §7 — thiếu policy: chặn autonomous hoàn toàn; người chỉ đi tiếp nếu là founder/admin.
      if (p.isAutonomous) {
        throw APIError.failedPrecondition(
          `Không có stage transition policy cho ${p.toStage} — chặn chuyển stage tự động (fail-closed)`
        );
      }
      if (!privileged) {
        throw APIError.permissionDenied(
          "Chỉ founder/admin mới được chuyển stage khi chưa cấu hình policy"
        );
      }
    } else if (!assess.gatePassed) {
      if (!p.override) {
        throw APIError.failedPrecondition(
          `Gate chưa đạt để lên ${p.toStage}: ${assess.blockers.join("; ")}`
        );
      }
      // M1 §7 — override phải có thẩm quyền; agent tự động không được tự override.
      if (p.isAutonomous) {
        throw APIError.permissionDenied("Agent tự động không được tự override gate");
      }
      if (!privileged) {
        throw APIError.permissionDenied(
          "Override gate chỉ dành cho founder/admin (hoặc approval workflow — M4)"
        );
      }
      // Override hợp lệ: KHÔNG xóa kết quả gate — ghi overrideFlag + reason vào journal bên dưới.
    }
  }

  // M4 §2 — policy_version của edge (currentStage -> toStage) để ghi vào journal.
  const [edgePolicy] = await db
    .select({ policyVersion: stageTransitionPolicies.policyVersion })
    .from(stageTransitionPolicies)
    .where(
      and(
        eq(stageTransitionPolicies.workspaceId, p.workspaceId),
        eq(stageTransitionPolicies.fromStage, currentStage),
        eq(stageTransitionPolicies.toStage, p.toStage)
      )
    )
    .limit(1);

  const now = new Date();
  const transitionId = generateSnowflake();
  const fromVersion = ws.stageVersion;
  const nextVersion = fromVersion + 1;
  const source: TransitionParams["source"] = p.source ?? (p.isAutonomous ? "autonomous" : "manual");

  const evidenceSnapshot = {
    evidenceCount: assessResult?.evidenceCount ?? 0,
    capturedAt: now.toISOString(),
  };
  const evaluationResult = assessResult
    ? {
        gatePassed: assessResult.gatePassed,
        policyMissing: assessResult.policyMissing,
        blockers: assessResult.blockers,
        recommendedStage: assessResult.recommendedStage,
      }
    : null;

  await db.transaction(async (tx) => {
    // Optimistic CAS theo stage_version: hai transition đồng thời cùng xuất phát
    // một stage ⇒ chỉ một thắng, cái kia rowCount=0 ⇒ APIError.aborted (rollback).
    const updated = await tx
      .update(identityWorkspaces)
      .set({
        lifecycleStage: p.toStage,
        stageEnteredAt: now,
        stageVersion: nextVersion,
        updatedAt: now,
      })
      .where(
        and(
          eq(identityWorkspaces.id, p.workspaceId),
          eq(identityWorkspaces.stageVersion, fromVersion)
        )
      )
      .returning({ id: identityWorkspaces.id });

    if (updated.length === 0) {
      throw APIError.aborted(
        "stage_version đã thay đổi (transition đồng thời) — hãy re-evaluate rồi thử lại"
      );
    }

    await tx.insert(workspaceStageTransitions).values({
      id: transitionId,
      workspaceId: p.workspaceId,
      fromStage: currentStage,
      toStage: p.toStage,
      reason: p.reason,
      actorMemberId: p.actorMemberId || null,
      actorRole: p.actorRole ?? null,
      overrideFlag: !!p.override,
      overrideApprovalRef: p.overrideApprovalRef ?? null,
      source,
      stageVersionFrom: fromVersion,
      policyVersion: edgePolicy?.policyVersion ?? null,
      evidenceSnapshot,
      evaluationResult,
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
    noop: false,
    stageVersion: nextVersion,
  };
}

export async function listVentureStageTransitions(workspaceId: bigint) {
  return db
    .select()
    .from(workspaceStageTransitions)
    .where(eq(workspaceStageTransitions.workspaceId, workspaceId))
    .orderBy(desc(workspaceStageTransitions.decidedAt));
}
