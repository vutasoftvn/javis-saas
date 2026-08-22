import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface SalesOpportunityRow {
  id: number;
  workspace_id: number;
  account_id: number;
  primary_contact_id: number | null;
  owner_id: number | null;
  source_lead_id: number | null;
  product: string | null;
  stage: string;
  estimated_value: number | null;
  currency: string;
  probability: number | null;
  expected_close_date: Date | null;
  won_reason: string | null;
  lost_reason: string | null;
  created_at: Date;
  updated_at: Date;
}

function rowToOpportunity(row: SalesOpportunityRow): SalesOpportunity {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    primaryContactId: row.primary_contact_id,
    ownerId: row.owner_id,
    sourceLeadId: row.source_lead_id,
    product: row.product,
    stage: row.stage,
    estimatedValue: row.estimated_value,
    currency: row.currency,
    probability: row.probability,
    expectedCloseDate: row.expected_close_date ? row.expected_close_date.toISOString() : null,
    wonReason: row.won_reason,
    lostReason: row.lost_reason,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createSalesOpportunity = api(
  { method: "POST", path: "/commercial/opportunities", expose: true },
  async (params: CreateSalesOpportunityParams): Promise<SalesOpportunity> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      INSERT INTO sales.sales_opportunities (workspace_id, account_id, primary_contact_id, source_lead_id, product, estimated_value)
      VALUES (
        ${params.workspaceId}, ${params.accountId}, ${params.primaryContactId ?? null},
        ${params.sourceLeadId ?? null}, ${params.product ?? null}, ${params.estimatedValue ?? null}
      )
      RETURNING id, workspace_id, account_id, primary_contact_id, owner_id, source_lead_id,
        product, stage, estimated_value, currency, probability, expected_close_date, won_reason, lost_reason,
        created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create sales opportunity");
    return rowToOpportunity(row);
  }
);

export const getSalesOpportunity = api(
  { method: "GET", path: "/commercial/opportunities/:id", expose: true },
  async ({ id }: { id: number }): Promise<SalesOpportunity> => {
    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      SELECT id, workspace_id, account_id, primary_contact_id, owner_id, source_lead_id,
        product, stage, estimated_value, currency, probability, expected_close_date, won_reason, lost_reason,
        created_at, updated_at
      FROM sales.sales_opportunities WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
    return rowToOpportunity(row);
  }
);

export const updateOpportunityStage = api(
  { method: "POST", path: "/commercial/opportunities/:id/stage", expose: true },
  async ({ id, stage }: { id: number; stage: string }): Promise<SalesOpportunity> => {
    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      UPDATE sales.sales_opportunities SET stage = ${stage}, updated_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, account_id, primary_contact_id, owner_id, source_lead_id,
        product, stage, estimated_value, currency, probability, expected_close_date, won_reason, lost_reason,
        created_at, updated_at
    `;
    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
    return rowToOpportunity(row);
  }
);
