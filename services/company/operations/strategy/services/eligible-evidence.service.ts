import { and, eq, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { evidence } from "../../../shared/db/schema/strategy";
import type { TenantContext } from "../../../shared/types/tenant_context";

export interface EvidenceEligibilityCandidate {
  status: string;
  deletedAt: Date | null;
  freshUntil: Date | null;
}

export type EvidenceExclusionReason = "DELETED" | "NOT_APPROVED" | "EXPIRED";

export interface ExcludedEvidenceItem {
  evidence: typeof evidence.$inferSelect;
  reason: EvidenceExclusionReason;
}

export interface EligibleEvidenceResult {
  eligible: (typeof evidence.$inferSelect)[];
  excluded: ExcludedEvidenceItem[];
}

/**
 * Hàm pure kiểm tra tính hợp lệ của evidence tại một thời điểm `at`.
 * Chỉ evidence đã "approved", chưa bị xóa (deletedAt == null),
 * và chưa hết hạn (freshUntil == null hoặc freshUntil > at) mới được coi là hợp lệ.
 */
export function isEvidenceEligible(
  e: EvidenceEligibilityCandidate,
  at: Date = new Date()
): boolean {
  if (e.deletedAt !== null) return false;
  if (e.status !== "approved") return false;
  if (e.freshUntil !== null && e.freshUntil.getTime() <= at.getTime()) return false;
  return true;
}

export function getEvidenceExclusionReason(
  e: EvidenceEligibilityCandidate,
  at: Date = new Date()
): EvidenceExclusionReason | null {
  if (e.deletedAt !== null) return "DELETED";
  if (e.status !== "approved") return "NOT_APPROVED";
  if (e.freshUntil !== null && e.freshUntil.getTime() <= at.getTime()) return "EXPIRED";
  return null;
}

export interface SelectEligibleEvidenceParams {
  projectId?: string | bigint | number;
  at?: Date;
  requireApproved?: boolean;
}

/**
 * Lấy danh sách evidence hợp lệ trong workspace/project theo thời điểm `at`.
 * Dùng chung cho W-stage gates, PMF scoreboard và project transitions.
 */
export async function selectEligibleEvidence(
  ctx: TenantContext,
  params: SelectEligibleEvidenceParams = {}
): Promise<EligibleEvidenceResult> {
  const wsId = BigInt(ctx.workspaceId);
  const at = params.at || new Date();

  const conditions = [eq(evidence.workspaceId, wsId)];
  if (params.projectId !== undefined) {
    conditions.push(eq(evidence.projectId, BigInt(params.projectId)));
  }

  const allRows = await db
    .select()
    .from(evidence)
    .where(and(...conditions));

  const eligible: (typeof evidence.$inferSelect)[] = [];
  const excluded: ExcludedEvidenceItem[] = [];

  for (const row of allRows) {
    const reason = getEvidenceExclusionReason(row, at);
    if (reason === null) {
      eligible.push(row);
    } else {
      excluded.push({ evidence: row, reason });
    }
  }

  return { eligible, excluded };
}
