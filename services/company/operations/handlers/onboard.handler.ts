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

// Kiểu response khai báo tường minh: Encore sinh schema response từ annotation
// của handler; handler không khai báo kiểu trả về thì HTTP trả body rỗng
// (e2e test_startup_os_founder_flow nhận 200 với body rỗng).
export interface OnboardSessionResponse {
  sessionId: string;
  status: string;
}

export interface OnboardTurnResponse {
  turnId: string;
}

export interface OnboardDimensionResponse {
  success: boolean;
  dimension: string;
  recordId: string;
}

export interface OnboardSnapshotResponse {
  snapshotId: string;
  capturedAt: string;
}

export interface CurrentCompanyContextResponse {
  workspaceId: string;
  fullContext: Record<string, unknown>;
}

export interface CadenceStatusResponse {
  cadences: DimensionCadenceStatus[];
}

export interface SeedCadenceResponse {
  success: boolean;
  workspaceId: string;
}

export const startOnboardSession = api(
  { method: "POST", path: "/operations/onboard/sessions", expose: true },
  async (params: WithAuth<StartSessionParams>): Promise<OnboardSessionResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.STARTUP_OS_SESSION_START],
    });
    const { authorization: _auth, ...input } = params;
    return startOnboardSessionService(input);
  }
);

export const recordConversationTurn = api(
  { method: "POST", path: "/operations/onboard/turns", expose: true },
  async (params: WithAuth<RecordTurnParams>): Promise<OnboardTurnResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return recordConversationTurnService(input);
  }
);

export const updateOnboardDimension = api(
  { method: "POST", path: "/operations/onboard/dimensions/:dimension", expose: true },
  async (params: WithAuth<UpdateDimensionParams>): Promise<OnboardDimensionResponse> => {
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
  async (params: WithAuth<CreateSnapshotParams>): Promise<OnboardSnapshotResponse> => {
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
  async (params: WithAuth<{ workspaceId: Query<string> }>): Promise<CadenceStatusResponse> => {
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
  async (params: WithAuth<{ workspaceId: string }>): Promise<SeedCadenceResponse> => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    await seedReviewCadenceService(BigInt(params.workspaceId));
    return { success: true, workspaceId: params.workspaceId };
  }
);
