import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  MarketingContextDTO,
  UpdateProductMarketingParams,
  UpdateCustomerResearchParams,
  UpdateOfferArchitectureParams,
  UpdateTwelveWeekPlanParams,
  SubmitForReviewParams,
  ApproveContextParams,
  getMarketingContextService,
  updateProductMarketingService,
  updateCustomerResearchService,
  updateOfferArchitectureService,
  updateTwelveWeekPlanService,
  submitForReviewService,
  approveContextService,
} from "../services/marketing-context.service";

export { MarketingContextDTO };

export interface GetMarketingContextRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateProductMarketingRequest extends UpdateProductMarketingParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateCustomerResearchRequest extends UpdateCustomerResearchParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateOfferArchitectureRequest extends UpdateOfferArchitectureParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateTwelveWeekPlanRequest extends UpdateTwelveWeekPlanParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface SubmitForReviewRequest extends SubmitForReviewParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface ApproveContextRequest extends ApproveContextParams {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

// 1. GET /commercial/marketing-context
export const getMarketingContext = api(
  { expose: true, method: "GET", path: "/commercial/marketing-context" },
  async ({ workspaceId, authorization }: GetMarketingContextRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getMarketingContextService(ctx);
  }
);

// 2. PATCH /commercial/marketing-context/product-marketing
export const updateProductMarketing = api(
  { expose: true, method: "PATCH", path: "/commercial/marketing-context/product-marketing" },
  async ({ workspaceId, authorization, ...params }: UpdateProductMarketingRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateProductMarketingService(ctx, params);
  }
);

// 3. PATCH /commercial/marketing-context/customer-research
export const updateCustomerResearch = api(
  { expose: true, method: "PATCH", path: "/commercial/marketing-context/customer-research" },
  async ({ workspaceId, authorization, ...params }: UpdateCustomerResearchRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateCustomerResearchService(ctx, params);
  }
);

// 4. PATCH /commercial/marketing-context/offer-architecture
export const updateOfferArchitecture = api(
  { expose: true, method: "PATCH", path: "/commercial/marketing-context/offer-architecture" },
  async ({ workspaceId, authorization, ...params }: UpdateOfferArchitectureRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateOfferArchitectureService(ctx, params);
  }
);

// 5. PATCH /commercial/marketing-context/twelve-week-plan
export const updateTwelveWeekPlan = api(
  { expose: true, method: "PATCH", path: "/commercial/marketing-context/twelve-week-plan" },
  async ({ workspaceId, authorization, ...params }: UpdateTwelveWeekPlanRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateTwelveWeekPlanService(ctx, params);
  }
);

// 6. POST /commercial/marketing-context/submit-review
export const submitMarketingContextForReview = api(
  { expose: true, method: "POST", path: "/commercial/marketing-context/submit-review" },
  async ({ workspaceId, authorization, ...params }: SubmitForReviewRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return submitForReviewService(ctx, params);
  }
);

// 7. POST /commercial/marketing-context/approve
export const approveMarketingContext = api(
  { expose: true, method: "POST", path: "/commercial/marketing-context/approve" },
  async ({ workspaceId, authorization, ...params }: ApproveContextRequest): Promise<MarketingContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return approveContextService(ctx, params);
  }
);
