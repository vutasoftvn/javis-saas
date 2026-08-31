import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  CampaignAssetDTO,
  createCampaignMvpService,
  createExperimentMvpService,
  createObjectiveService,
  getMarketingContextMvpService,
  getObservedMetricsMvpService,
  listAssetsMvpService,
  listCampaignsMvpService,
  listExperimentsMvpService,
  listObjectivesService,
  MarketingCampaignDTO,
  MarketingExperimentDTO,
  MarketingObjectiveDTO,
  MarketingObservedMetricDTO,
  updateMarketingContextMvpService,
} from "../services/marketing-mvp.service";
import type { MarketingContextDTO } from "./marketing-context.handler";

export interface MvpHeaderRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateMarketingContextMvpRequest extends MvpHeaderRequest {
  category?: string;
  positioningStatement?: string;
  alternatives?: any[];
  differentiators?: any[];
  brandVoice?: Record<string, any>;
}

export const updateMarketingContextMvp = api(
  { expose: true, method: "PUT", path: "/commercial/marketing-context" },
  async (req: UpdateMarketingContextMvpRequest): Promise<MvpSuccess<MarketingContextDTO>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return updateMarketingContextMvpService(ctx, {
      category: req.category,
      positioningStatement: req.positioningStatement,
      alternatives: req.alternatives,
      differentiators: req.differentiators,
      brandVoice: req.brandVoice,
    });
  }
);

// ─── Objectives ───

export const listObjectives = api(
  { expose: true, method: "GET", path: "/commercial/marketing/objectives" },
  async ({ workspaceId, authorization }: MvpHeaderRequest): Promise<MvpSuccess<readonly MarketingObjectiveDTO[]>> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listObjectivesService(ctx);
  }
);

export interface CreateObjectiveRequest extends MvpHeaderRequest {
  title: string;
  description?: string;
  targetMetric?: string;
  targetValue?: number;
  startDate?: string;
  endDate?: string;
}

export const createObjective = api(
  { expose: true, method: "POST", path: "/commercial/marketing/objectives" },
  async (req: CreateObjectiveRequest): Promise<MvpSuccess<MarketingObjectiveDTO>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createObjectiveService(ctx, {
      title: req.title,
      description: req.description,
      targetMetric: req.targetMetric,
      targetValue: req.targetValue,
      startDate: req.startDate,
      endDate: req.endDate,
    });
  }
);

// ─── Campaigns ───

export const listCampaignsMvp = api(
  { expose: true, method: "GET", path: "/commercial/marketing/campaigns" },
  async ({ workspaceId, authorization }: MvpHeaderRequest): Promise<MvpSuccess<readonly MarketingCampaignDTO[]>> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listCampaignsMvpService(ctx);
  }
);

export interface CreateCampaignMvpRequest extends MvpHeaderRequest {
  name: string;
  funnelStage?: string;
  channels?: unknown;
  budget?: number;
  startDate?: string;
  endDate?: string;
}

export const createCampaignMvp = api(
  { expose: true, method: "POST", path: "/commercial/marketing/campaigns" },
  async (req: CreateCampaignMvpRequest): Promise<MvpSuccess<MarketingCampaignDTO>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createCampaignMvpService(ctx, {
      name: req.name,
      funnelStage: req.funnelStage,
      channels: req.channels,
      budget: req.budget,
      startDate: req.startDate,
      endDate: req.endDate,
    });
  }
);

// ─── Assets ───

export interface ListAssetsRequest extends MvpHeaderRequest {
  campaignId?: Query<string>;
}

export const listAssetsMvp = api(
  { expose: true, method: "GET", path: "/commercial/marketing/assets" },
  async (req: ListAssetsRequest): Promise<MvpSuccess<readonly CampaignAssetDTO[]>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return listAssetsMvpService(ctx, req.campaignId);
  }
);

// ─── Experiments ───

export const listExperimentsMvp = api(
  { expose: true, method: "GET", path: "/commercial/marketing/experiments" },
  async ({ workspaceId, authorization }: MvpHeaderRequest): Promise<MvpSuccess<readonly MarketingExperimentDTO[]>> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listExperimentsMvpService(ctx);
  }
);

export interface CreateExperimentMvpRequest extends MvpHeaderRequest {
  campaignId?: string;
  name: string;
  hypothesis: string;
  baselineMetric?: string;
  baselineValue?: number;
  targetMetric?: string;
  targetValue?: number;
}

export const createExperimentMvp = api(
  { expose: true, method: "POST", path: "/commercial/marketing/experiments" },
  async (req: CreateExperimentMvpRequest): Promise<MvpSuccess<MarketingExperimentDTO>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createExperimentMvpService(ctx, {
      campaignId: req.campaignId,
      name: req.name,
      hypothesis: req.hypothesis,
      baselineMetric: req.baselineMetric,
      baselineValue: req.baselineValue,
      targetMetric: req.targetMetric,
      targetValue: req.targetValue,
    });
  }
);

// ─── Observed Metrics ───

export interface GetObservedMetricsRequest extends MvpHeaderRequest {
  providerKey?: Query<string>;
}

export const getObservedMetricsMvp = api(
  { expose: true, method: "GET", path: "/commercial/marketing/metrics/observed" },
  async (req: GetObservedMetricsRequest): Promise<MvpSuccess<readonly MarketingObservedMetricDTO[]>> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getObservedMetricsMvpService(ctx, req.providerKey);
  }
);
