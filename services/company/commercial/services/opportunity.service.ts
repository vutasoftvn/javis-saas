import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { salesOpportunities } = schema;

export interface SalesOpportunity {
  id: number;
  workspaceId: number;
  accountId: number;
  primaryContactId: number | null;
  ownerId: number | null;
  sourceLeadId: number | null;
  product: string | null;
  stage: string;
  estimatedValue: number | null;
  currency: string;
  probability: number | null;
  expectedCloseDate: string | null;
  wonReason: string | null;
  lostReason: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSalesOpportunityParams {
  workspaceId: number;
  accountId: number;
  primaryContactId?: number;
  sourceLeadId?: number;
  product?: string;
  estimatedValue?: number;
}

function toOpportunity(row: typeof salesOpportunities.$inferSelect): SalesOpportunity {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    accountId: Number(row.accountId),
    primaryContactId: row.primaryContactId ? Number(row.primaryContactId) : null,
    ownerId: row.ownerId ? Number(row.ownerId) : null,
    sourceLeadId: row.sourceLeadId ? Number(row.sourceLeadId) : null,
    product: row.product,
    stage: row.stage,
    estimatedValue: row.estimatedValue,
    currency: row.currency,
    probability: row.probability,
    expectedCloseDate: row.expectedCloseDate ? String(row.expectedCloseDate) : null,
    wonReason: row.wonReason,
    lostReason: row.lostReason,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

async function getOpportunityRow(id: number) {
  const [row] = await db
    .select()
    .from(salesOpportunities)
    .where(eq(salesOpportunities.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
  return row;
}

export async function createSalesOpportunityService(
  params: CreateSalesOpportunityParams,
  authorization: string | undefined
): Promise<SalesOpportunity> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(salesOpportunities)
    .values({
      workspaceId: BigInt(params.workspaceId),
      accountId: BigInt(params.accountId),
      primaryContactId: params.primaryContactId ? BigInt(params.primaryContactId) : null,
      sourceLeadId: params.sourceLeadId ? BigInt(params.sourceLeadId) : null,
      product: params.product || null,
      estimatedValue: params.estimatedValue ?? null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create sales opportunity");
  return toOpportunity(row);
}

export async function getSalesOpportunityService(
  id: number,
  authorization: string | undefined
): Promise<SalesOpportunity> {
  const row = await getOpportunityRow(id);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toOpportunity(row);
}

export async function updateOpportunityStageService(
  id: number,
  stage: string,
  authorization: string | undefined
): Promise<SalesOpportunity> {
  const existing = await getOpportunityRow(id);
  await requireWorkspaceAccess(authorization, Number(existing.workspaceId));

  const [row] = await db
    .update(salesOpportunities)
    .set({
      stage,
      updatedAt: new Date(),
    })
    .where(eq(salesOpportunities.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
  return toOpportunity(row);
}
