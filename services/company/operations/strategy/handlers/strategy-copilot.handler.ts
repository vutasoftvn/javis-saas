import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  getStrategyAgentManifestsService,
  configureStrategyAgentService,
  proposePestelSignalsService,
  proposeTowsOptionsService,
  proposeInitiativesService,
  StrategyCopilotProfileManifest,
  ProposePestelSignalsResult,
  ProposeTowsOptionsResult,
  ProposeInitiativesResult,
  CandidatePestelSignal,
  CandidateTowsOption,
  CandidateInitiative,
} from "../services/strategy-copilot.service";
import type { OwnerAgentProfile } from "../../services/ai-member.service";

// --------------------------------------------------------------------------
// AGENT MANIFESTS & CONFIGURATION
// --------------------------------------------------------------------------

interface GetStrategyAgentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

interface StrategyAgentsListResponse {
  agents: StrategyCopilotProfileManifest[];
}

export const getStrategyAgents = api(
  { method: "GET", path: "/operations/strategy/agents", expose: true },
  async (params: GetStrategyAgentsParams): Promise<StrategyAgentsListResponse> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const agents = await getStrategyAgentManifestsService(ctx);
    return { agents };
  }
);

interface ConfigureStrategyAgentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  profile: OwnerAgentProfile;
  activateMember?: boolean;
}

export const configureStrategyAgent = api(
  { method: "POST", path: "/operations/strategy/agents/configure", expose: true },
  async (params: ConfigureStrategyAgentParams): Promise<StrategyCopilotProfileManifest> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return configureStrategyAgentService(ctx, {
      profile: params.profile,
      activateMember: params.activateMember,
    });
  }
);

// --------------------------------------------------------------------------
// PROPOSAL APIS
// --------------------------------------------------------------------------

interface ProposePestelSignalsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  strategicObjectiveId: string;
  signals: CandidatePestelSignal[];
}

export const proposePestelSignals = api(
  { method: "POST", path: "/operations/strategy/copilot/propose-pestel", expose: true },
  async (params: ProposePestelSignalsParams): Promise<ProposePestelSignalsResult> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return proposePestelSignalsService(ctx, {
      strategicObjectiveId: params.strategicObjectiveId,
      signals: params.signals,
    });
  }
);

interface ProposeTowsOptionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  strategicObjectiveId: string;
  options: CandidateTowsOption[];
}

export const proposeTowsOptions = api(
  { method: "POST", path: "/operations/strategy/copilot/propose-tows", expose: true },
  async (params: ProposeTowsOptionsParams): Promise<ProposeTowsOptionsResult> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return proposeTowsOptionsService(ctx, {
      strategicObjectiveId: params.strategicObjectiveId,
      options: params.options,
    });
  }
);

interface ProposeInitiativesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  strategicObjectiveId?: string;
  towsOptionId?: string;
  initiatives: CandidateInitiative[];
}

export const proposeInitiatives = api(
  { method: "POST", path: "/operations/strategy/copilot/propose-initiatives", expose: true },
  async (params: ProposeInitiativesParams): Promise<ProposeInitiativesResult> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return proposeInitiativesService(ctx, {
      strategicObjectiveId: params.strategicObjectiveId,
      towsOptionId: params.towsOptionId,
      initiatives: params.initiatives,
    });
  }
);
