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
    // Fail-closed: không có policy ⇒ không khẳng định gate đã đạt.
    return {
      currentStage,
      recommendedStage,
      gatePassed: false,
      blockers: [
        `Chưa cấu hình stage transition policy cho ${recommendedStage} — fail-closed`,
      ],
      policyMissing: true,
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
    policyMissing: false,
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
