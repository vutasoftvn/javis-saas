import { api, Header } from "encore.dev/api";
import {
  MarketingCampaign,
  CreateMarketingCampaignRequest as BaseCreateMarketingCampaignRequest,
  CampaignAsset,
  CreateCampaignAssetRequest as BaseCreateCampaignAssetRequest,
  MarketingForm,
  CreateMarketingFormRequest as BaseCreateMarketingFormRequest,
  createCampaignService,
  listCampaignsService,
  createAssetService,
  createMarketingFormService,
} from "../services/marketing.service";

export { MarketingCampaign, CampaignAsset, MarketingForm };

export interface CreateMarketingCampaignRequest extends BaseCreateMarketingCampaignRequest {
  authorization?: Header<"Authorization">;
}
export interface CreateCampaignAssetRequest extends BaseCreateCampaignAssetRequest {
  authorization?: Header<"Authorization">;
}
export interface CreateMarketingFormRequest extends BaseCreateMarketingFormRequest {
  authorization?: Header<"Authorization">;
}

// ─── Marketing Campaigns Endpoints ───

export const createCampaign = api(
  { expose: true, method: "POST", path: "/commercial/campaigns" },
  async (req: CreateMarketingCampaignRequest): Promise<MarketingCampaign> => {
    return createCampaignService(req, req.authorization);
  }
);

export const listCampaigns = api(
  { expose: true, method: "GET", path: "/commercial/workspaces/:workspaceId/campaigns" },
  async (params: { workspaceId: string; authorization?: Header<"Authorization"> }): Promise<{ campaigns: MarketingCampaign[] }> => {
    const campaigns = await listCampaignsService(params.workspaceId, params.authorization);
    return { campaigns };
  }
);

// ─── Campaign Assets Endpoints ───

export const createAsset = api(
  { expose: true, method: "POST", path: "/commercial/campaign-assets" },
  async (req: CreateCampaignAssetRequest): Promise<CampaignAsset> => {
    return createAssetService(req, req.authorization);
  }
);

// ─── Marketing Forms Endpoints ───

export const createMarketingForm = api(
  { expose: true, method: "POST", path: "/commercial/marketing-forms" },
  async (req: CreateMarketingFormRequest): Promise<MarketingForm> => {
    return createMarketingFormService(req, req.authorization);
  }
);
