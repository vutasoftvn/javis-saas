import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceSnapshots,
  aiIncidents,
  dataProcessingAuthorizations,
} = schema;

/**
 * Điểm triển khai duy nhất cho scoped lookup của các resource AI compliance.
 * Mọi service (governance, snapshot, data-governance, incident-response) PHẢI
 * gọi qua đây thay vì tự viết lại `WHERE id = ...` — tránh trôi về id-only
 * implementation như đã xảy ra trước ADR-AI-COMPLIANCE-RUNTIME-001.
 *
 * Một ID hợp lệ nhưng thuộc workspace khác trả về APIError.notFound giống hệt
 * ID không tồn tại — không lộ oracle "tồn tại nhưng không có quyền".
 */

export async function getDeploymentInWorkspace(
  workspaceId: string | bigint,
  deploymentId: string | bigint
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(
      and(
        eq(workspaceAiDeployments.id, BigInt(deploymentId)),
        eq(workspaceAiDeployments.workspaceId, BigInt(workspaceId))
      )
    );

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  return deployment;
}

export async function getAssessmentInWorkspace(
  workspaceId: string | bigint,
  deploymentId: string | bigint,
  assessmentId: string | bigint
): Promise<typeof aiRiskAssessments.$inferSelect> {
  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(
      and(
        eq(aiRiskAssessments.id, BigInt(assessmentId)),
        eq(aiRiskAssessments.deploymentId, BigInt(deploymentId)),
        eq(aiRiskAssessments.workspaceId, BigInt(workspaceId))
      )
    );

  if (!assessment) {
    throw APIError.notFound("Assessment not found for this deployment");
  }

  return assessment;
}

export async function getComplianceSnapshotInWorkspace(
  workspaceId: string | bigint,
  snapshotId: string | bigint
): Promise<typeof aiComplianceSnapshots.$inferSelect> {
  const [snapshot] = await db
    .select()
    .from(aiComplianceSnapshots)
    .where(
      and(
        eq(aiComplianceSnapshots.id, BigInt(snapshotId)),
        eq(aiComplianceSnapshots.workspaceId, BigInt(workspaceId))
      )
    );

  if (!snapshot) {
    throw APIError.notFound("Compliance snapshot not found");
  }

  return snapshot;
}

export async function getIncidentInWorkspace(
  workspaceId: string | bigint,
  incidentId: string | bigint
): Promise<typeof aiIncidents.$inferSelect> {
  const [incident] = await db
    .select()
    .from(aiIncidents)
    .where(
      and(
        eq(aiIncidents.id, BigInt(incidentId)),
        eq(aiIncidents.workspaceId, BigInt(workspaceId))
      )
    );

  if (!incident) {
    throw APIError.notFound("AI incident not found");
  }

  return incident;
}

export async function getProcessingAuthorizationInWorkspace(
  workspaceId: string | bigint,
  authorizationId: string | bigint
): Promise<typeof dataProcessingAuthorizations.$inferSelect> {
  const [authorization] = await db
    .select()
    .from(dataProcessingAuthorizations)
    .where(
      and(
        eq(dataProcessingAuthorizations.id, BigInt(authorizationId)),
        eq(dataProcessingAuthorizations.workspaceId, BigInt(workspaceId))
      )
    );

  if (!authorization) {
    throw APIError.notFound("Processing authorization not found");
  }

  return authorization;
}
