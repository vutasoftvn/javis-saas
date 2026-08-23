import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { marketingCampaigns, campaignAssets, marketingForms } = schema;

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

function toCampaign(row: typeof marketingCampaigns.$inferSelect): MarketingCampaign {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    name: row.name,
    funnelStage: row.funnelStage,
    channels: (row.channels as string[]) || [],
    budget: row.budget,
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
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(marketingCampaigns)
    .values({
      workspaceId: BigInt(req.workspaceId),
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
  workspaceId: number,
  authorization: string | undefined
): Promise<MarketingCampaign[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

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
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(campaignAssets)
    .values({
      workspaceId: BigInt(req.workspaceId),
      campaignId: BigInt(req.campaignId),
      assetType: req.assetType,
      title: req.title,
      content: req.content,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create campaign asset");
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    campaignId: Number(row.campaignId),
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
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(marketingForms)
    .values({
      workspaceId: BigInt(req.workspaceId),
      title: req.title,
      slug: req.slug,
      fieldsSchema: req.fieldsSchema || [],
      isPublished: req.isPublished || false,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create marketing form");
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    title: row.title,
    slug: row.slug,
    fieldsSchema: (row.fieldsSchema as any[]) || [],
    isPublished: row.isPublished,
    createdAt: row.createdAt.toISOString(),
  };
}
