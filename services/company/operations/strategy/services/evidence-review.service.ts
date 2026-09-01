import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";
import { Evidence, toEvidence } from "./evidence-lifecycle.service";

const { evidence } = schema;

export interface ReviewEvidenceInput {
  id: string;
  action: "approve" | "reject";
  comment?: string;
}

export async function reviewEvidenceInWorkspace(
  ctx: TenantContext,
  params: ReviewEvidenceInput
): Promise<Evidence> {
  if (!params.action || !["approve", "reject"].includes(params.action)) {
    throw APIError.invalidArgument("action must be 'approve' or 'reject'");
  }

  assertLifecyclePrivileged(ctx.membershipRole, "reviewEvidence");
  const wsId = BigInt(ctx.workspaceId);

  const newStatus = params.action === "approve" ? "approved" : "rejected";
  const reviewedByMemberId = ctx.userId ? BigInt(ctx.userId) : null;
  const reviewedAt = new Date();

  const [row] = await db
    .update(evidence)
    .set({
      status: newStatus,
      reviewComment: params.comment ?? null,
      reviewedByMemberId,
      reviewedAt,
      updatedAt: reviewedAt,
    })
    .where(and(eq(evidence.id, BigInt(params.id)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Evidence not found");
  return toEvidence(row);
}
