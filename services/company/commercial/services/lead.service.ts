import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { salesLeads } = schema;

export interface SalesLead {
  id: string;
  workspaceId: string;
  keyResultId: string | null;
  accountId: string | null;
  contactId: string | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  source: string | null;
  sourceCampaignId: string | null;
  sourceExperimentId: string | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  fitScore: number | null;
  intentScore: number | null;
  engagementScore: number | null;
  qualificationStatus: string | null;
  ownerMemberId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSalesLeadParams {
  workspaceId: string;
  name: string;
  accountId?: string;
  contactId?: string;
  company?: string;
  value?: number;
  source?: string;
  ownerMemberId?: string;
}

function toSalesLead(row: typeof salesLeads.$inferSelect): SalesLead {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    keyResultId: row.keyResultId ? String(row.keyResultId) : null,
    accountId: row.accountId ? String(row.accountId) : null,
    contactId: row.contactId ? String(row.contactId) : null,
    name: row.name,
    company: row.company,
    stage: row.stage,
    value: row.value,
    source: row.source,
    sourceCampaignId: row.sourceCampaignId ? String(row.sourceCampaignId) : null,
    sourceExperimentId: row.sourceExperimentId ? String(row.sourceExperimentId) : null,
    utmSource: row.utmSource,
    utmMedium: row.utmMedium,
    utmCampaign: row.utmCampaign,
    fitScore: row.fitScore,
    intentScore: row.intentScore,
    engagementScore: row.engagementScore,
    qualificationStatus: row.qualificationStatus,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

async function getSalesLeadRow(id: string) {
  const [row] = await db
    .select()
    .from(salesLeads)
    .where(eq(salesLeads.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`sales lead ${id} not found`);
  return row;
}

export async function createSalesLeadService(
  params: CreateSalesLeadParams,
  authorization: string | undefined
): Promise<SalesLead> {
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(salesLeads)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(params.workspaceId)),
      accountId: params.accountId ? BigInt(String(params.accountId)) : null,
      contactId: params.contactId ? BigInt(String(params.contactId)) : null,
      name: params.name,
      company: params.company || null,
      value: params.value ?? null,
      source: params.source || null,
      ownerMemberId: params.ownerMemberId ? BigInt(String(params.ownerMemberId)) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create sales lead");
  return toSalesLead(row);
}

export async function getSalesLeadService(id: string, authorization: string | undefined): Promise<SalesLead> {
  const row = await getSalesLeadRow(id);
  await requireWorkspaceAccess(authorization, String(row.workspaceId));
  return toSalesLead(row);
}

export async function listSalesLeadsService(
  workspaceId: string,
  authorization: string | undefined
): Promise<SalesLead[]> {
  await requireWorkspaceAccess(authorization, String(workspaceId));

  const rows = await db
    .select()
    .from(salesLeads)
    .where(eq(salesLeads.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(salesLeads.createdAt));

  return rows.map(toSalesLead);
}

export async function updateLeadStageService(
  id: string,
  stage: string,
  authorization: string | undefined
): Promise<SalesLead> {
  const existing = await getSalesLeadRow(id);
  await requireWorkspaceAccess(authorization, String(existing.workspaceId));

  const [row] = await db
    .update(salesLeads)
    .set({
      stage,
      updatedAt: new Date(),
    })
    .where(eq(salesLeads.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`sales lead ${id} not found`);
  return toSalesLead(row);
}
