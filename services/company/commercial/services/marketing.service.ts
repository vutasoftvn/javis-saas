import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { marketingCampaigns, campaignAssets, marketingForms } = schema;

export interface MarketingCampaign {
  id: string;
  workspaceId: string;
  name: string;
  funnelStage: string;
  channels: string[];
  budget?: number | null;
  status: string;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateMarketingCampaignRequest {
  workspaceId: string;
  name: string;
  funnelStage?: string;
  channels?: string[];
  budget?: number;
  startDate?: string | null;
  endDate?: string | null;
}

export interface CampaignAsset {
  id: string;
  workspaceId: string;
  campaignId: string;
  assetType: string;
  title: string;
  content: string;
  status?: string;
  createdAt: string;
}

export interface CreateCampaignAssetRequest {
  workspaceId: string;
  campaignId: string;
  assetType: string;
  title: string;
  content: string;
}

export interface MarketingForm {
  id: string;
  workspaceId: string;
  title: string;
  slug: string;
  fieldsSchema: any[];
  isPublished: boolean;
  createdAt: string;
}

export interface CreateMarketingFormRequest {
  workspaceId: string;
  title: string;
  slug: string;
  fieldsSchema?: any[];
  isPublished?: boolean;
}

function toCampaign(row: typeof marketingCampaigns.$inferSelect): MarketingCampaign {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    name: row.name,
    funnelStage: row.funnelStage,
    channels: (row.channels as string[]) || [],
    budget: row.budget !== null && row.budget !== undefined ? Number(row.budget) : null,
    status: row.status,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createCampaignService(
  req: CreateMarketingCampaignRequest,
  authorization: string | undefined
): Promise<MarketingCampaign> {
  if (!req.workspaceId || !req.name) {
    throw APIError.invalidArgument("workspaceId and name are required");
  }
  await requireWorkspaceAccess(authorization, String(req.workspaceId));

  const [row] = await db
    .insert(marketingCampaigns)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(req.workspaceId)),
      name: req.name,
      funnelStage: req.funnelStage || "discover",
      channels: req.channels || [],
      budget: req.budget ?? 0,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create marketing campaign");
  return toCampaign(row);
}

export async function listCampaignsService(
  workspaceId: string,
  authorization: string | undefined
): Promise<MarketingCampaign[]> {
  await requireWorkspaceAccess(authorization, String(workspaceId));

  const rows = await db
    .select()
    .from(marketingCampaigns)
    .where(eq(marketingCampaigns.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(marketingCampaigns.id));

  return rows.map(toCampaign);
}

export async function createAssetService(
  req: CreateCampaignAssetRequest,
  authorization: string | undefined
): Promise<CampaignAsset> {
  if (!req.workspaceId || !req.campaignId || !req.assetType || !req.title || !req.content) {
    throw APIError.invalidArgument("workspaceId, campaignId, assetType, title, and content are required");
  }
  await requireWorkspaceAccess(authorization, String(req.workspaceId));

  const [row] = await db
    .insert(campaignAssets)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(req.workspaceId)),
      campaignId: BigInt(String(req.campaignId)),
      assetType: req.assetType,
      title: req.title,
      content: req.content,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create campaign asset");
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    campaignId: String(row.campaignId),
    assetType: row.assetType,
    title: row.title,
    content: row.content,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createMarketingFormService(
  req: CreateMarketingFormRequest,
  authorization: string | undefined
): Promise<MarketingForm> {
  if (!req.workspaceId || !req.title || !req.slug) {
    throw APIError.invalidArgument("workspaceId, title, and slug are required");
  }
  await requireWorkspaceAccess(authorization, String(req.workspaceId));

  const [row] = await db
    .insert(marketingForms)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(req.workspaceId)),
      title: req.title,
      slug: req.slug,
      fieldsSchema: req.fieldsSchema || [],
      isPublished: req.isPublished || false,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create marketing form");
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    title: row.title,
    slug: row.slug,
    fieldsSchema: (row.fieldsSchema as any[]) || [],
    isPublished: row.isPublished,
    createdAt: row.createdAt.toISOString(),
  };
}
