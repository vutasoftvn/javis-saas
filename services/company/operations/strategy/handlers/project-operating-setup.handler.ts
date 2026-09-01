import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  getProjectOperatingSetup,
  saveProjectOperatingSetup,
  activateProjectOperatingSetup,
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
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
      weeklyReviewWeekday: params.weeklyReviewWeekday,
      weeklyReviewTime: params.weeklyReviewTime,
      firstWeekOutcome: params.firstWeekOutcome,
      firstWeekActions: params.firstWeekActions,
    });
  }
);
