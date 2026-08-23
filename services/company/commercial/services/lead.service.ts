import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { salesLeads } = schema;

export interface SalesLead {
  id: number;
  workspaceId: number;
  keyResultId: number | null;
  accountId: number | null;
  contactId: number | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  source: string | null;
  sourceCampaignId: number | null;
  sourceExperimentId: number | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  fitScore: number | null;
  intentScore: number | null;
  engagementScore: number | null;
  qualificationStatus: string | null;
  ownerId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSalesLeadParams {
  workspaceId: number;
  name: string;
  accountId?: number;
  contactId?: number;
  company?: string;
  value?: number;
  source?: string;
  ownerId?: number;
}

function toSalesLead(row: typeof salesLeads.$inferSelect): SalesLead {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    keyResultId: row.keyResultId ? Number(row.keyResultId) : null,
    accountId: row.accountId ? Number(row.accountId) : null,
    contactId: row.contactId ? Number(row.contactId) : null,
    name: row.name,
    company: row.company,
    stage: row.stage,
    value: row.value,
    source: row.source,
    sourceCampaignId: row.sourceCampaignId ? Number(row.sourceCampaignId) : null,
    sourceExperimentId: row.sourceExperimentId ? Number(row.sourceExperimentId) : null,
    utmSource: row.utmSource,
    utmMedium: row.utmMedium,
    utmCampaign: row.utmCampaign,
    fitScore: row.fitScore,
    intentScore: row.intentScore,
    engagementScore: row.engagementScore,
    qualificationStatus: row.qualificationStatus,
    ownerId: row.ownerId ? Number(row.ownerId) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

async function getSalesLeadRow(id: number) {
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
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(salesLeads)
    .values({
      workspaceId: BigInt(params.workspaceId),
      accountId: params.accountId ? BigInt(params.accountId) : null,
      contactId: params.contactId ? BigInt(params.contactId) : null,
      name: params.name,
      company: params.company || null,
      value: params.value ?? null,
      source: params.source || null,
      ownerId: params.ownerId ? BigInt(params.ownerId) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create sales lead");
  return toSalesLead(row);
}

export async function getSalesLeadService(id: number, authorization: string | undefined): Promise<SalesLead> {
  const row = await getSalesLeadRow(id);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toSalesLead(row);
}

export async function listSalesLeadsService(
  workspaceId: number,
  authorization: string | undefined
): Promise<SalesLead[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(salesLeads)
    .where(eq(salesLeads.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(salesLeads.createdAt));

  return rows.map(toSalesLead);
}

export async function updateLeadStageService(
  id: number,
  stage: string,
  authorization: string | undefined
): Promise<SalesLead> {
  const existing = await getSalesLeadRow(id);
  await requireWorkspaceAccess(authorization, Number(existing.workspaceId));

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
