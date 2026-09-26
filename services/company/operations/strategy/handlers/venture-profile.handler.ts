import { api, Header } from "encore.dev/api";
import {
  requireWorkspaceAccess,
  requireWorkspaceWrite,
} from "../../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../../shared/auth/agent-capabilities";
import {
  getVentureProfileService,
  updateVentureProfileService,
  VentureProfileView,
} from "../services/venture-profile.service";

export interface GetVentureProfileParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface UpdateVentureProfileParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  problemStatement?: string | null;
  targetCustomer?: string | null;
  industry?: string | null;
  geography?: string | null;
  currency?: string | null;
  timezone?: string | null;
  founderGoal?: string | null;
  initialRunwayMonths?: number | null;
}

export interface VentureProfileResponse {
  profile: VentureProfileView;
}

export const getVentureProfile = api(
  { method: "GET", path: "/operations/strategy/venture-profile", expose: true },
  async (params: GetVentureProfileParams): Promise<VentureProfileResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.VENTURE_PROFILE_READ],
    });
    return { profile: await getVentureProfileService(BigInt(ctx.workspaceId)) };
  }
);

// Chỉ người dùng có quyền ghi được sửa; agent (venture.profile.propose_update)
// cố ý chưa được mở vì capability đó ghi thẳng, chưa qua bước duyệt.
export const updateVentureProfile = api(
  { method: "PUT", path: "/operations/strategy/venture-profile", expose: true },
  async (params: UpdateVentureProfileParams): Promise<VentureProfileResponse> => {
    const ctx = await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _authorization, workspaceId: _workspaceId, ...input } = params;
    return { profile: await updateVentureProfileService(BigInt(ctx.workspaceId), input) };
  }
);
