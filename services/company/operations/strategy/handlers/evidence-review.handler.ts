import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { assertLifecyclePrivileged } from "../services/lifecycle-authorization.service";
import { Evidence } from "./evidence.handler";

const { evidence } = schema;

export interface ReviewEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  action: "approve" | "reject";
  comment?: string;
}

export const reviewEvidence = api(
  { method: "POST", path: "/operations/strategy/evidence/:id/review", expose: true },
  async (params: ReviewEvidenceParams): Promise<Evidence> => {
    if (!params.action || !["approve", "reject"].includes(params.action)) {
      throw APIError.invalidArgument("action must be 'approve' or 'reject'");
    }

    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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

    return {
      id: row.id.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      experimentId: row.experimentId ? row.experimentId.toString() : null,
      sourceType: row.sourceType,
      claim: row.claim,
      strength: row.strength,
      confidence: row.confidence,
      supportsOrRefutes: row.supportsOrRefutes,
      status: row.status,
      reviewComment: row.reviewComment ?? null,
      reviewedByMemberId: row.reviewedByMemberId ? row.reviewedByMemberId.toString() : null,
      reviewedAt: row.reviewedAt ? row.reviewedAt.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);
