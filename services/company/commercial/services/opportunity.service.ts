import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { salesOpportunities } = schema;

export interface SalesOpportunity {
  id: string;
  workspaceId: string;
  accountId: string;
  primaryContactId: string | null;
  ownerMemberId: string | null;
  sourceLeadId: string | null;
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
  workspaceId: string;
  accountId: string;
  primaryContactId?: string;
  ownerMemberId?: string;
  sourceLeadId?: string;
  product?: string;
  estimatedValue?: number;
}

function toOpportunity(row: typeof salesOpportunities.$inferSelect): SalesOpportunity {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: String(row.accountId),
    primaryContactId: row.primaryContactId ? String(row.primaryContactId) : null,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    sourceLeadId: row.sourceLeadId ? String(row.sourceLeadId) : null,
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

export async function createSalesOpportunityService(
  params: CreateSalesOpportunityParams,
  authorization: string | undefined
): Promise<SalesOpportunity> {
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(salesOpportunities)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(params.workspaceId)),
      accountId: BigInt(String(params.accountId)),
      primaryContactId: params.primaryContactId ? BigInt(String(params.primaryContactId)) : null,
      ownerMemberId: params.ownerMemberId ? BigInt(String(params.ownerMemberId)) : null,
      sourceLeadId: params.sourceLeadId ? BigInt(String(params.sourceLeadId)) : null,
      product: params.product || null,
      estimatedValue: params.estimatedValue ?? null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create sales opportunity");
  return toOpportunity(row);
}

export async function getSalesOpportunityService(
  id: string,
  ctx: TenantContext
): Promise<SalesOpportunity> {
  const [row] = await db
    .select()
    .from(salesOpportunities)
    .where(and(eq(salesOpportunities.id, BigInt(id)), eq(salesOpportunities.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
  return toOpportunity(row);
}

export async function updateOpportunityStageService(
  id: string,
  stage: string,
  ctx: TenantContext
): Promise<SalesOpportunity> {
  const [row] = await db
    .update(salesOpportunities)
    .set({
      stage,
      updatedAt: new Date(),
    })
    .where(and(eq(salesOpportunities.id, BigInt(id)), eq(salesOpportunities.workspaceId, BigInt(ctx.workspaceId))))
    .returning();

  if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
  return toOpportunity(row);
}

