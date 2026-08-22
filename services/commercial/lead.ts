import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface SalesLeadRow {
  id: number;
  workspace_id: number;
  key_result_id: number | null;
  account_id: number | null;
  contact_id: number | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  source: string | null;
  source_campaign_id: number | null;
  source_experiment_id: number | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  fit_score: number | null;
  intent_score: number | null;
  engagement_score: number | null;
  qualification_status: string | null;
  owner_id: number | null;
  created_at: Date;
  updated_at: Date;
}

function rowToSalesLead(row: SalesLeadRow): SalesLead {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    keyResultId: row.key_result_id,
    accountId: row.account_id,
    contactId: row.contact_id,
    name: row.name,
    company: row.company,
    stage: row.stage,
    value: row.value,
    source: row.source,
    sourceCampaignId: row.source_campaign_id,
    sourceExperimentId: row.source_experiment_id,
    utmSource: row.utm_source,
    utmMedium: row.utm_medium,
    utmCampaign: row.utm_campaign,
    fitScore: row.fit_score,
    intentScore: row.intent_score,
    engagementScore: row.engagement_score,
    qualificationStatus: row.qualification_status,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createSalesLead = api(
  { method: "POST", path: "/commercial/leads", expose: true },
  async (params: CreateSalesLeadParams): Promise<SalesLead> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<SalesLeadRow>`
      INSERT INTO sales.sales_leads (workspace_id, account_id, contact_id, name, company, value, source, owner_id)
      VALUES (
        ${params.workspaceId}, ${params.accountId ?? null}, ${params.contactId ?? null}, ${params.name},
        ${params.company ?? null}, ${params.value ?? null}, ${params.source ?? null}, ${params.ownerId ?? null}
      )
      RETURNING id, workspace_id, key_result_id, account_id, contact_id, name, company, stage, value,
        source, source_campaign_id, source_experiment_id, utm_source, utm_medium, utm_campaign,
        fit_score, intent_score, engagement_score, qualification_status, owner_id, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create sales lead");
    return rowToSalesLead(row);
  }
);

export const getSalesLead = api(
  { method: "GET", path: "/commercial/leads/:id", expose: true },
  async ({ id }: { id: number }): Promise<SalesLead> => {
    const row = await commercialDB.queryRow<SalesLeadRow>`
      SELECT id, workspace_id, key_result_id, account_id, contact_id, name, company, stage, value,
        source, source_campaign_id, source_experiment_id, utm_source, utm_medium, utm_campaign,
        fit_score, intent_score, engagement_score, qualification_status, owner_id, created_at, updated_at
      FROM sales.sales_leads WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`sales lead ${id} not found`);
    return rowToSalesLead(row);
  }
);

export const listSalesLeads = api(
  { method: "GET", path: "/commercial/leads", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ leads: SalesLead[] }> => {
    const rows = commercialDB.query<SalesLeadRow>`
      SELECT id, workspace_id, key_result_id, account_id, contact_id, name, company, stage, value,
        source, source_campaign_id, source_experiment_id, utm_source, utm_medium, utm_campaign,
        fit_score, intent_score, engagement_score, qualification_status, owner_id, created_at, updated_at
      FROM sales.sales_leads WHERE workspace_id = ${workspaceId}
      ORDER BY created_at DESC
    `;
    const leads: SalesLead[] = [];
    for await (const row of rows) {
      leads.push(rowToSalesLead(row));
    }
    return { leads };
  }
);

export const updateLeadStage = api(
  { method: "POST", path: "/commercial/leads/:id/stage", expose: true },
  async ({ id, stage }: { id: number; stage: string }): Promise<SalesLead> => {
    const row = await commercialDB.queryRow<SalesLeadRow>`
      UPDATE sales.sales_leads SET stage = ${stage}, updated_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, key_result_id, account_id, contact_id, name, company, stage, value,
        source, source_campaign_id, source_experiment_id, utm_source, utm_medium, utm_campaign,
        fit_score, intent_score, engagement_score, qualification_status, owner_id, created_at, updated_at
    `;
    if (!row) throw APIError.notFound(`sales lead ${id} not found`);
    return rowToSalesLead(row);
  }
);
