import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  getProjectOperatingSetup,
  saveProjectOperatingSetup,
  activateProjectOperatingSetup,
  requestKickoffSuggestion,
  applyKickoffSuggestionResult,
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
  KickoffSuggestionDispatchResult,
  OperatingSetupStatus,
  EvidenceLevel,
  BasicKickoffStage,
  FirstWeekAction,
} from "../services/project-operating-setup.service";
import { Project } from "../../services/project.service";

export type {
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
  KickoffSuggestionDispatchResult,
  OperatingSetupStatus,
  EvidenceLevel,
  BasicKickoffStage,
  FirstWeekAction,
};

export interface GetProjectOperatingSetupParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface PutProjectOperatingSetupParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  targetCustomer?: string | null;
  problemStatement?: string | null;
  evidenceLevel?: EvidenceLevel | null;
  selectedStage?: BasicKickoffStage | null;
  stageDurationWeeks?: number | null;
  roundStartDate?: string | null;
  weeklyReviewWeekday?: number | null;
  weeklyReviewTime?: string | null;
  firstWeekOutcome?: string | null;
  firstWeekActions?: Array<{ id?: string; title: string }>;
}

export interface ActivateProjectOperatingSetupParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  targetCustomer: string;
  problemStatement: string;
  evidenceLevel: EvidenceLevel;
  selectedStage: BasicKickoffStage;
  stageDurationWeeks: number;
  roundStartDate?: string | null;
  weeklyReviewWeekday: number;
  weeklyReviewTime: string;
  firstWeekOutcome: string;
  firstWeekActions: Array<{ id?: string; title: string }>;
}

export interface ActivateProjectOperatingSetupResponse {
  setup: ProjectOperatingSetupView;
  project: Project;
}

// ── GET /operations/projects/:id/operating-setup ──
export const getProjectOperatingSetupEndpoint = api(
  { method: "GET", path: "/operations/projects/:id/operating-setup", expose: true },
  async (params: GetProjectOperatingSetupParams): Promise<ProjectOperatingSetupView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getProjectOperatingSetup(ctx, params.id);
  }
);

// ── PUT /operations/projects/:id/operating-setup ──
export const putProjectOperatingSetupEndpoint = api(
  { method: "PUT", path: "/operations/projects/:id/operating-setup", expose: true },
  async (params: PutProjectOperatingSetupParams): Promise<ProjectOperatingSetupView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return saveProjectOperatingSetup(ctx, params.id, {
      targetCustomer: params.targetCustomer,
      problemStatement: params.problemStatement,
      evidenceLevel: params.evidenceLevel,
      selectedStage: params.selectedStage,
      stageDurationWeeks: params.stageDurationWeeks,
      roundStartDate: params.roundStartDate,
      weeklyReviewWeekday: params.weeklyReviewWeekday,
      weeklyReviewTime: params.weeklyReviewTime,
      firstWeekOutcome: params.firstWeekOutcome,
      firstWeekActions: params.firstWeekActions,
    });
  }
);

// ── POST /operations/projects/:id/operating-setup/activate ──
export const activateProjectOperatingSetupEndpoint = api(
  { method: "POST", path: "/operations/projects/:id/operating-setup/activate", expose: true },
  async (params: ActivateProjectOperatingSetupParams): Promise<ActivateProjectOperatingSetupResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return activateProjectOperatingSetup(ctx, params.id, {
      targetCustomer: params.targetCustomer,
      problemStatement: params.problemStatement,
      evidenceLevel: params.evidenceLevel,
      selectedStage: params.selectedStage,
      stageDurationWeeks: params.stageDurationWeeks,
      roundStartDate: params.roundStartDate,
      weeklyReviewWeekday: params.weeklyReviewWeekday,
      weeklyReviewTime: params.weeklyReviewTime,
      firstWeekOutcome: params.firstWeekOutcome,
      firstWeekActions: params.firstWeekActions,
    });
  }
);

export interface RequestKickoffSuggestionParams {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

// ── POST /operations/projects/:id/kickoff-suggestion ──
export const requestKickoffSuggestionEndpoint = api(
  { method: "POST", path: "/operations/projects/:id/kickoff-suggestion", expose: true },
  async (params: RequestKickoffSuggestionParams): Promise<KickoffSuggestionDispatchResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return requestKickoffSuggestion(ctx, params.id);
  }
);

export interface ApplyKickoffSuggestionResultParams {
  id: string;
  runId: string;
  status: string;
  outcome?: string;
  actions?: string[];
  serviceToken?: Header<"X-Cosa-Service-Token">;
}

// ── POST /operations/projects/:id/kickoff-suggestion/result (Internal callback from COSA) ──
export const applyKickoffSuggestionResultEndpoint = api(
  { method: "POST", path: "/operations/projects/:id/kickoff-suggestion/result", expose: true },
  async (params: ApplyKickoffSuggestionResultParams): Promise<{ applied: boolean }> => {
    const expectedToken = process.env.COSA_SERVICE_TOKEN || "local-dev-service-token";
    if (!params.serviceToken || params.serviceToken !== expectedToken) {
      throw APIError.unauthenticated("invalid or missing service token");
    }
    if (params.status !== "completed" && params.status !== "failed") {
      throw APIError.invalidArgument("status must be 'completed' or 'failed'");
    }
    return applyKickoffSuggestionResult({
      projectId: params.id,
      runId: params.runId,
      status: params.status,
      outcome: params.outcome,
      actions: params.actions,
    });
  }
);
