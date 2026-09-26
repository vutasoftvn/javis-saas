import { api, Header, Query } from "encore.dev/api";
import {
  startOnboardSessionService,
  recordConversationTurnService,
  updateDimensionService,
  createSnapshotService,
  assembleCurrentCompanyContext,
  getCadenceStatusService,
  seedReviewCadenceService,
  DimensionCadenceStatus,
} from "../services/onboard.service";
import { requireWorkspaceAccess, requireWorkspaceWrite } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";

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

// Kiểu response PHẢI khai báo tường minh trên chữ ký handler — xem ghi chú ở
// goals.handler.ts (Encore không suy luận kiểu trả về; thiếu annotation -> 200
// body rỗng, "Độ tươi ngữ cảnh 7 chiều" trên Flutter không tải được).
export interface StartOnboardSessionResponse {
  sessionId: string;
  status: string;
}

export interface RecordConversationTurnResponse {
  turnId: string;
}

export interface UpdateOnboardDimensionResponse {
  success: boolean;
  dimension: string;
  recordId: string;
}

export interface CreateOnboardSnapshotResponse {
  snapshotId: string;
  capturedAt: string;
}

export interface CurrentCompanyContextResponse {
  workspaceId: string;
  fullContext: Record<string, unknown>;
}

export interface OnboardCadenceStatusResponse {
  cadences: DimensionCadenceStatus[];
}

export interface SeedOnboardCadenceResponse {
  success: boolean;
  workspaceId: string;
}

export const startOnboardSession = api(
  { method: "POST", path: "/operations/onboard/sessions", expose: true },
  async (params: WithAuth<StartSessionParams>): Promise<StartOnboardSessionResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.STARTUP_OS_SESSION_START],
    });
    const { authorization: _auth, ...input } = params;
    return startOnboardSessionService(input);
  }
);

export const recordConversationTurn = api(
  { method: "POST", path: "/operations/onboard/turns", expose: true },
  async (params: WithAuth<RecordTurnParams>): Promise<RecordConversationTurnResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return recordConversationTurnService(input);
  }
);

export const updateOnboardDimension = api(
  { method: "POST", path: "/operations/onboard/dimensions/:dimension", expose: true },
  async (params: WithAuth<UpdateDimensionParams>): Promise<UpdateOnboardDimensionResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.STARTUP_OS_DIMENSION_UPDATE],
    });
    return updateDimensionService({
      workspaceId: params.workspaceId,
      sessionId: params.sessionId,
      dimension: params.dimension,
      data: params.data,
    });
  }
);

export const createOnboardSnapshot = api(
  { method: "POST", path: "/operations/onboard/snapshots", expose: true },
  async (params: WithAuth<CreateSnapshotParams>): Promise<CreateOnboardSnapshotResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.STARTUP_OS_SNAPSHOT_CREATE],
    });
    const { authorization: _auth, ...input } = params;
    return createSnapshotService(input);
  }
);

export const getCurrentCompanyContext = api(
  { method: "GET", path: "/operations/onboard/context/current", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>): Promise<CurrentCompanyContextResponse> => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.STARTUP_OS_CONTEXT_READ, AGENT_CAP.STARTUP_OS_GOAL_ADVISORY],
    });
    const fullContext = await assembleCurrentCompanyContext(BigInt(params.workspaceId));
    return { workspaceId: params.workspaceId, fullContext };
  }
);

export const getOnboardCadenceStatus = api(
  { method: "GET", path: "/operations/onboard/cadence/status", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>): Promise<OnboardCadenceStatusResponse> => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId, {
      agentCapabilities: [
        AGENT_CAP.STARTUP_OS_CADENCE_STATUS,
        AGENT_CAP.STARTUP_OS_CADENCE_ADVISORY,
        AGENT_CAP.STARTUP_OS_GOAL_ADVISORY,
      ],
    });
    return getCadenceStatusService(params.workspaceId);
  }
);

export const seedOnboardCadence = api(
  { method: "POST", path: "/operations/onboard/cadence/seed", expose: true },
  async (params: WithAuth<{ workspaceId: string }>): Promise<SeedOnboardCadenceResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    await seedReviewCadenceService(BigInt(params.workspaceId));
    return { success: true, workspaceId: params.workspaceId };
  }
);
