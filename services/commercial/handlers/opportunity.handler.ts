import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

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

export const createSalesOpportunity = api(
  { method: "POST", path: "/commercial/opportunities", expose: true },
  async (params: CreateSalesOpportunityParams): Promise<SalesOpportunity> => {
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
);

export const getSalesOpportunity = api(
  { method: "GET", path: "/commercial/opportunities/:id", expose: true },
  async ({ id }: { id: number }): Promise<SalesOpportunity> => {
    const [row] = await db
      .select()
      .from(salesOpportunities)
      .where(eq(salesOpportunities.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
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
);

export const updateOpportunityStage = api(
  { method: "POST", path: "/commercial/opportunities/:id/stage", expose: true },
  async ({ id, stage }: { id: number; stage: string }): Promise<SalesOpportunity> => {
    const [row] = await db
      .update(salesOpportunities)
      .set({
        stage,
        updatedAt: new Date(),
      })
      .where(eq(salesOpportunities.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
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
);
