import { api, Header } from "encore.dev/api";
import {
  getVentureProfileService,
  upsertVentureProfileService,
  VentureProfileView,
} from "../services/venture-profile.service";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";

export interface GetVentureProfileParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface GetVentureProfileResponse {
  profile: VentureProfileView | null;
}

export interface UpsertVentureProfileParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  problemStatement?: string;
  targetCustomer?: string;
  industry?: string;
  geography?: string;
  currency?: string;
  timezone?: string;
  founderGoal?: string;
  initialRunwayMonths?: number;
}

export const getVentureProfile = api(
  { method: "GET", path: "/operations/strategy/venture-profile", expose: true },
  async (params: GetVentureProfileParams): Promise<GetVentureProfileResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const profile = await getVentureProfileService(BigInt(ctx.workspaceId));
    return { profile };
  }
);

export const putVentureProfile = api(
  { method: "PUT", path: "/operations/strategy/venture-profile", expose: true },
  async (params: UpsertVentureProfileParams): Promise<VentureProfileView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return upsertVentureProfileService({
      workspaceId: BigInt(ctx.workspaceId),
      problemStatement: params.problemStatement,
      targetCustomer: params.targetCustomer,
      industry: params.industry,
      geography: params.geography,
      currency: params.currency,
      timezone: params.timezone,
      founderGoal: params.founderGoal,
      initialRunwayMonths: params.initialRunwayMonths,
    });
  }
);
