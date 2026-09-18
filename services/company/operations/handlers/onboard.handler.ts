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

type WithAuth<T> = Omit<T, "authorization"> & { authorization?: Header<"Authorization"> };

export interface StartSessionParams {
  workspaceId: string;
  sessionType: "initial" | "partial_update" | "event_driven";
  summary?: string;
  metadata?: Record<string, unknown>;
}

export interface RecordTurnParams {
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
    return startOnboardSessionService(params);
  }
);

export const recordConversationTurn = api(
  { method: "POST", path: "/operations/onboard/turns", expose: true },
  async (params: WithAuth<RecordTurnParams>) => {
    return recordConversationTurnService(params);
  }
);

export const updateOnboardDimension = api(
  { method: "POST", path: "/operations/onboard/dimensions/:dimension", expose: true },
  async (params: WithAuth<UpdateDimensionParams>) => {
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
    return createSnapshotService(params);
  }
);

export const getCurrentCompanyContext = api(
  { method: "GET", path: "/operations/onboard/context/current", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    const fullContext = await assembleCurrentCompanyContext(BigInt(params.workspaceId));
    return { workspaceId: params.workspaceId, fullContext };
  }
);

export const getOnboardCadenceStatus = api(
  { method: "GET", path: "/operations/onboard/cadence/status", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    return getCadenceStatusService(params.workspaceId);
  }
);

export const seedOnboardCadence = api(
  { method: "POST", path: "/operations/onboard/cadence/seed", expose: true },
  async (params: WithAuth<{ workspaceId: string }>) => {
    await seedReviewCadenceService(BigInt(params.workspaceId));
    return { success: true, workspaceId: params.workspaceId };
  }
);
