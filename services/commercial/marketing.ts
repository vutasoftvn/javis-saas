import { api, APIError } from "encore.dev/api";
import { SQLDatabase } from "encore.dev/storage/sqldb";

const db = SQLDatabase.named("commercial");

export interface MarketingCampaign {
  id: number;
  workspaceId: number;
  name: string;
  funnelStage: string;
  channels: string[];
  budget: number;
  status: string;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateMarketingCampaignRequest {
  workspaceId: number;
  name: string;
  funnelStage?: string;
  channels?: string[];
  budget?: number;
  startDate?: string | null;
  endDate?: string | null;
}

export interface CampaignAsset {
  id: number;
  workspaceId: number;
  campaignId: number;
  assetType: string;
  title: string;
  content: string;
  status: string;
  createdAt: string;
}

export interface CreateCampaignAssetRequest {
  workspaceId: number;
  campaignId: number;
  assetType: string;
  title: string;
  content: string;
}

export interface MarketingForm {
  id: number;
  workspaceId: number;
  title: string;
  slug: string;
  fieldsSchema: any[];
  isPublished: boolean;
  createdAt: string;
}

export interface CreateMarketingFormRequest {
  workspaceId: number;
  title: string;
  slug: string;
  fieldsSchema?: any[];
  isPublished?: boolean;
}

// ─── Marketing Campaigns Endpoints ───

export const createCampaign = api(
  { expose: true, method: "POST", path: "/commercial/campaigns" },
  async (req: CreateMarketingCampaignRequest): Promise<MarketingCampaign> => {
    if (!req.workspaceId || !req.name) {
      throw APIError.invalidArgument("workspaceId and name are required");
    }

    const row = await db.queryRow<MarketingCampaign>`
      INSERT INTO commercial.marketing_campaigns (
        workspace_id, name, funnel_stage, channels, budget,
        start_date, end_date
      ) VALUES (
        ${req.workspaceId}, ${req.name},
        ${req.funnelStage ?? "discover"},
        ${JSON.stringify(req.channels ?? [])},
        ${req.budget ?? 0},
        ${req.startDate ?? null}, ${req.endDate ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", name, funnel_stage as "funnelStage",
        channels, budget, status, start_date as "startDate", end_date as "endDate",
        created_at as "createdAt", updated_at as "updatedAt"
    `;
    if (!row) throw APIError.internal("Failed to create marketing campaign");
    return row;
  }
);

export const listCampaigns = api(
  { expose: true, method: "GET", path: "/commercial/workspaces/:workspaceId/campaigns" },
  async (params: { workspaceId: number }): Promise<{ campaigns: MarketingCampaign[] }> => {
    const rows = db.query<MarketingCampaign>`
      SELECT
        id, workspace_id as "workspaceId", name, funnel_stage as "funnelStage",
        channels, budget, status, start_date as "startDate", end_date as "endDate",
        created_at as "createdAt", updated_at as "updatedAt"
      FROM commercial.marketing_campaigns
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const campaigns: MarketingCampaign[] = [];
    for await (const row of rows) campaigns.push(row);
    return { campaigns };
  }
);

// ─── Campaign Assets Endpoints ───

export const createAsset = api(
  { expose: true, method: "POST", path: "/commercial/campaign-assets" },
  async (req: CreateCampaignAssetRequest): Promise<CampaignAsset> => {
    if (!req.workspaceId || !req.campaignId || !req.assetType || !req.title || !req.content) {
      throw APIError.invalidArgument("workspaceId, campaignId, assetType, title, and content are required");
    }

    const row = await db.queryRow<CampaignAsset>`
      INSERT INTO commercial.campaign_assets (
        workspace_id, campaign_id, asset_type, title, content
      ) VALUES (
        ${req.workspaceId}, ${req.campaignId}, ${req.assetType},
        ${req.title}, ${req.content}
      )
      RETURNING
        id, workspace_id as "workspaceId", campaign_id as "campaignId",
        asset_type as "assetType", title, content, status,
        created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create campaign asset");
    return row;
  }
);

// ─── Marketing Forms Endpoints ───

export const createMarketingForm = api(
  { expose: true, method: "POST", path: "/commercial/marketing-forms" },
  async (req: CreateMarketingFormRequest): Promise<MarketingForm> => {
    if (!req.workspaceId || !req.title || !req.slug) {
      throw APIError.invalidArgument("workspaceId, title, and slug are required");
    }

    const row = await db.queryRow<MarketingForm>`
      INSERT INTO commercial.marketing_forms (
        workspace_id, title, slug, fields_schema, is_published
      ) VALUES (
        ${req.workspaceId}, ${req.title}, ${req.slug},
        ${JSON.stringify(req.fieldsSchema ?? [])},
        ${req.isPublished ?? false}
      )
      RETURNING
        id, workspace_id as "workspaceId", title, slug,
        fields_schema as "fieldsSchema", is_published as "isPublished",
        created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create marketing form");
    return row;
  }
);
