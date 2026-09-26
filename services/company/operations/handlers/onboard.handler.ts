import { api, Header, Query } from "encore.dev/api";
import {
  startOnboardSessionService,
  recordConversationTurnService,
  updateDimensionService,
  createSnapshotService,
  assembleCurrentCompanyContext,
  getCadenceStatusService,
  seedReviewCadenceService,
  OnboardDimension,
} from "../services/onboard.service";
import { requireWorkspaceAccess, requireWorkspaceWrite } from "../../shared/auth/workspace-access";

type WithAuth<T> = Omit<T, "authorization"> & { authorization?: Header<"Authorization"> };

export interface StartSessionParams {
  workspaceId: string;
  sessionType: "initial" | "partial_update" | "event_driven";
  summary?: string;
  metadata?: Record<string, unknown>;
}

export interface RecordTurnParams {
  workspaceId: string;
  sessionId: string;
  turnNumber: number;
  role: "user" | "assistant" | "system";
  content: string;
  dimension?: string;
}

export interface UpdateDimensionParams {
  dimension: string;
  workspaceId: string;
  sessionId: string;
  data: any;
}

export interface CreateSnapshotParams {
  workspaceId: string;
  sessionId: string;
  changeReason?: string;
  changedDimensions?: string[];
}

export const startOnboardSession = api(
  { method: "POST", path: "/operations/onboard/sessions", expose: true },
  async (params: WithAuth<StartSessionParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return startOnboardSessionService(input);
  }
);

export const recordConversationTurn = api(
  { method: "POST", path: "/operations/onboard/turns", expose: true },
  async (params: WithAuth<RecordTurnParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return recordConversationTurnService(input);
  }
);

export const updateOnboardDimension = api(
  { method: "POST", path: "/operations/onboard/dimensions/:dimension", expose: true },
  async (params: WithAuth<UpdateDimensionParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    return updateDimensionService({
      workspaceId: params.workspaceId,
      sessionId: params.sessionId,
      dimension: params.dimension as OnboardDimension,
      data: params.data,
    });
  }
);

export const createOnboardSnapshot = api(
  { method: "POST", path: "/operations/onboard/snapshots", expose: true },
  async (params: WithAuth<CreateSnapshotParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return createSnapshotService(input);
  }
);

export const getCurrentCompanyContext = api(
  { method: "GET", path: "/operations/onboard/context/current", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const fullContext = await assembleCurrentCompanyContext(BigInt(params.workspaceId));
    return { workspaceId: params.workspaceId, fullContext };
  }
);

export const getOnboardCadenceStatus = api(
  { method: "GET", path: "/operations/onboard/cadence/status", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getCadenceStatusService(params.workspaceId);
  }
);

export const seedOnboardCadence = api(
  { method: "POST", path: "/operations/onboard/cadence/seed", expose: true },
  async (params: WithAuth<{ workspaceId: string }>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    await seedReviewCadenceService(BigInt(params.workspaceId));
    return { success: true, workspaceId: params.workspaceId };
  }
);
