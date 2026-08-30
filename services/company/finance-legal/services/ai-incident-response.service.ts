import { APIError } from "encore.dev/api";
import { eq, and, gte } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { suspendAiDeployment } from "./ai-compliance-governance.service";
import { getDeploymentInWorkspace, getIncidentInWorkspace } from "./ai-compliance-access.service";

const { aiIncidents, aiIncidentActions } = schema;

export interface ReportAiIncidentInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  incidentType: string;
  summary: string;
  dataCategories?: string[];
  rootCause?: string;
  mitigation?: string;
  reportedByMemberId?: string | bigint;
}

export interface ResolveAiIncidentInput {
  workspaceId: string | bigint;
  incidentId: string | bigint;
  resolvedByMemberId?: string | bigint;
  actionTaken: string;
  mitigation?: string;
}

export interface IncidentReportResult extends Record<string, any> {
  id: bigint;
  breakerTripped: boolean;
}

export async function evaluateCircuitBreakers(
  deploymentId: string | bigint
): Promise<{ trip: boolean; reason?: string }> {
  const depId = BigInt(deploymentId);
  const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

  const recentIncidents = await db
    .select()
    .from(aiIncidents)
    .where(
      and(
        eq(aiIncidents.deploymentId, depId),
        gte(aiIncidents.createdAt, twentyFourHoursAgo)
      )
    );

  const criticalCount = recentIncidents.filter((i) => i.severity === "CRITICAL").length;
  const highCount = recentIncidents.filter((i) => i.severity === "HIGH").length;

  if (criticalCount >= 3) {
    return {
      trip: true,
      reason: `Breaker tripped: ${criticalCount} CRITICAL incidents in past 24 hours (threshold: 3)`,
    };
  }

  if (highCount >= 5) {
    return {
      trip: true,
      reason: `Breaker tripped: ${highCount} HIGH incidents in past 24 hours (threshold: 5)`,
    };
  }

  return { trip: false };
}

export async function reportAiIncident(
  input: ReportAiIncidentInput
): Promise<IncidentReportResult> {
  const incidentId = generateSnowflake();
  const now = new Date();

  const [incident] = await db
    .insert(aiIncidents)
    .values({
      id: incidentId,
      workspaceId: BigInt(input.workspaceId),
      deploymentId: BigInt(input.deploymentId),
      severity: input.severity,
      status: "OPEN",
      detectedAt: now,
      dataCategories: input.dataCategories || [],
      summary: input.summary,
      notificationRationale: input.rootCause,
    })
    .returning();

  const breaker = await evaluateCircuitBreakers(input.deploymentId);

  if (input.severity === "CRITICAL" || breaker.trip) {
    const reason = breaker.trip
      ? breaker.reason || "Circuit breaker tripped due to incident frequency"
      : `Critical AI incident: ${input.summary}`;

    await suspendAiDeployment({
      workspaceId: input.workspaceId,
      deploymentId: String(input.deploymentId),
      rationale: reason,
      suspendedByMemberId: input.reportedByMemberId,
    });

    const actionId = generateSnowflake();
    await db.insert(aiIncidentActions).values({
      id: actionId,
      workspaceId: BigInt(input.workspaceId),
      incidentId: incident.id,
      actionType: "EMERGENCY_SUSPEND",
      description: reason,
      takenByMemberId: input.reportedByMemberId ? BigInt(input.reportedByMemberId) : BigInt(0),
    });

    return { ...incident, breakerTripped: breaker.trip };
  }

  return { ...incident, breakerTripped: false };
}

export async function openAiIncident(input: {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  detectedAt?: string;
  dataCategories?: string[];
  summary?: string;
}) {
  // Xác nhận deployment thuộc đúng workspaceId của caller trước khi mở
  // incident — trước đây hàm này tự suy ra workspaceId từ deployment khi
  // caller không truyền, không hề kiểm tra caller có quyền trên deployment
  // đó hay không (cross-workspace IDOR).
  const deployment = await getDeploymentInWorkspace(input.workspaceId, input.deploymentId);
  return reportAiIncident({
    workspaceId: deployment.workspaceId,
    deploymentId: deployment.id,
    severity: input.severity,
    incidentType: "OPERATIONAL_FAILURE",
    summary: input.summary || `${input.severity} incident detected`,
    dataCategories: input.dataCategories,
  });
}


export async function resolveAiIncident(
  input: ResolveAiIncidentInput
): Promise<typeof aiIncidents.$inferSelect> {
  const incident = await getIncidentInWorkspace(input.workspaceId, input.incidentId);
  const now = new Date();
  const [updated] = await db
    .update(aiIncidents)
    .set({
      status: "CLOSED",
      closedAt: now,
      notificationRationale: input.mitigation,
      updatedAt: now,
    })
    .where(and(eq(aiIncidents.id, incident.id), eq(aiIncidents.workspaceId, BigInt(input.workspaceId))))
    .returning();

  if (!updated) {
    throw APIError.notFound("AI incident not found");
  }

  const actionId = generateSnowflake();
  await db.insert(aiIncidentActions).values({
    id: actionId,
    workspaceId: updated.workspaceId,
    incidentId: updated.id,
    actionType: "RESOLVE_INCIDENT",
    description: input.actionTaken,
    takenByMemberId: input.resolvedByMemberId ? BigInt(input.resolvedByMemberId) : BigInt(0),
  });

  return updated;
}
