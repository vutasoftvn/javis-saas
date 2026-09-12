import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { assertCommercialProjectInWorkspace } from "./project-record-link.service";
import {
  ProjectLeadRepository,
  ProjectLeadInput,
  ProjectLeadView,
} from "./project-lead-repository";

const { salesLeads, leadFieldValues, leadFieldDefinitions } = schema;

export async function createProjectLeadService(
  ctx: TenantContext,
  projectId: string,
  input: ProjectLeadInput
): Promise<ProjectLeadView> {
  await assertCommercialProjectInWorkspace(ctx, projectId);
  return ProjectLeadRepository.createLead(ctx.workspaceId, projectId, input);
}

export async function listProjectLeadsService(
  ctx: TenantContext,
  projectId: string,
  options?: { limit?: number; offset?: number }
): Promise<ProjectLeadView[]> {
  await assertCommercialProjectInWorkspace(ctx, projectId);
  return ProjectLeadRepository.listLeads(ctx.workspaceId, projectId, options);
}

export async function getProjectLeadService(
  ctx: TenantContext,
  projectId: string,
  leadId: string
): Promise<ProjectLeadView> {
  await assertCommercialProjectInWorkspace(ctx, projectId);

  const [row] = await db
    .select()
    .from(salesLeads)
    .where(
      and(
        eq(salesLeads.id, BigInt(leadId)),
        eq(salesLeads.workspaceId, BigInt(ctx.workspaceId)),
        eq(salesLeads.projectId, BigInt(projectId))
      )
    )
    .limit(1);

  if (!row) {
    throw APIError.notFound("Không tìm thấy lead trong project này");
  }

  // Tải custom field values
  const values = await db
    .select({
      stableKey: leadFieldDefinitions.stableKey,
      val: leadFieldValues.valueJson,
    })
    .from(leadFieldValues)
    .innerJoin(
      leadFieldDefinitions,
      eq(leadFieldValues.fieldDefinitionId, leadFieldDefinitions.id)
    )
    .where(eq(leadFieldValues.leadId, BigInt(leadId)));

  const fieldValues: Record<string, unknown> = {};
  for (const v of values) {
    fieldValues[v.stableKey] = v.val;
  }

  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    name: row.name,
    company: row.company,
    stage: row.stage,
    value: row.value,
    source: row.source,
    leadSourceId: row.leadSourceId ? String(row.leadSourceId) : null,
    provenanceEventId: row.provenanceEventId ? String(row.provenanceEventId) : null,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    utmSource: row.utmSource,
    utmMedium: row.utmMedium,
    utmCampaign: row.utmCampaign,
    utmContent: row.utmContent,
    utmTerm: row.utmTerm,
    fitScore: row.fitScore,
    intentScore: row.intentScore,
    engagementScore: row.engagementScore,
    qualificationStatus: row.qualificationStatus,
    disqualificationReason: row.disqualificationReason,
    fieldValues,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}
