import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  ProjectOperatingLoop,
  OkrObjectiveDto,
  KeyResultDto,
  InitiativeDto,
  CycleDto,
  WeeklyPlanDto,
  WeeklyCommitmentDto,
  TaskDto,
  AdvanceCycleWeekResultDto,
  getProjectOperatingLoop,
  createObjectiveAuthorized,
  createKeyResultAuthorized,
  createInitiativeAuthorized,
  createCycleAuthorized,
  createWeeklyPlanAuthorized,
  createWeeklyCommitmentAuthorized,
  createTaskAuthorized,
  advanceTaskService,
  advanceCycleWeekAuthorized,
  verifyProjectInWorkspace,
} from "../services/project-operating-loop.service";

export interface ProjectLoopParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export interface CreateObjectiveBody {
  title: string;
  why?: string | null;
  ownerMemberId?: string | null;
}

export interface CreateKeyResultBody {
  objectiveId: string;
  title: string;
  metricId?: string | null;
  targetValue?: number | null;
  unit?: string | null;
}

export interface CreateInitiativeBody {
  keyResultId: string;
  title: string;
  description?: string | null;
  intendedOutcome?: string | null;
  ownerMemberId?: string | null;
}

export interface CreateCycleBody {
  theme?: string | null;
  visionStatement?: string | null;
  durationWeeks?: number;
  timezone?: string;
  startLocalDate?: string;
  startDate?: string;
  endDate?: string;
}

export interface CreateWeeklyPlanBody {
  cycleId: string;
  weekNo: number;
  focus?: string | null;
  mission?: string | null;
  startDate?: string;
  endDate?: string;
}

export interface CreateWeeklyCommitmentBody {
  weeklyPlanId: string;
  title: string;
  initiativeId?: string | null;
  plannedEffort?: string | null;
  ownerMemberId?: string | null;
  purposeType?: string;
  purposeRef?: string | null;
}

export interface CreateTaskBody {
  title: string;
  weeklyCommitmentId?: string | null;
  initiativeId?: string | null;
  priority?: string;
  plannedStartAt?: string;
  dueAt?: string;
  status?: string;
}

export interface AdvanceTaskParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  taskId: string;
  status: string;
}

export interface AdvanceCycleWeekBody {
  expectedCurrentWeek: number;
  reflection: string;
  executionScore?: number;
  outcomeScore?: number;
}

export interface AdvanceCycleWeekParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  cycleId: string;
}

export const getProjectOperatingLoopApi = api(
  { expose: true, method: "GET", path: "/operations/projects/:projectId/operating-loop" },
  async (params: ProjectLoopParams): Promise<ProjectOperatingLoop> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getProjectOperatingLoop(ctx, params.projectId);
  }
);

export const createObjectiveApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/objectives" },
  async (params: ProjectLoopParams & CreateObjectiveBody): Promise<OkrObjectiveDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createObjectiveAuthorized(ctx, {
      projectId: params.projectId,
      title: params.title,
      why: params.why,
      ownerMemberId: params.ownerMemberId,
    });
  }
);

export const createKeyResultApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/key-results" },
  async (params: ProjectLoopParams & CreateKeyResultBody): Promise<KeyResultDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createKeyResultAuthorized(ctx, {
      projectId: params.projectId,
      objectiveId: params.objectiveId,
      title: params.title,
      metricId: params.metricId,
      targetValue: params.targetValue,
      unit: params.unit,
    });
  }
);

export const createInitiativeApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/initiatives" },
  async (params: ProjectLoopParams & CreateInitiativeBody): Promise<InitiativeDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createInitiativeAuthorized(ctx, {
      projectId: params.projectId,
      keyResultId: params.keyResultId,
      title: params.title,
      description: params.description,
      intendedOutcome: params.intendedOutcome,
      ownerMemberId: params.ownerMemberId,
    });
  }
);

export const createCycleApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/cycles" },
  async (params: ProjectLoopParams & CreateCycleBody): Promise<CycleDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createCycleAuthorized(ctx, {
      projectId: params.projectId,
      theme: params.theme,
      visionStatement: params.visionStatement,
      durationWeeks: params.durationWeeks,
      timezone: params.timezone,
      startLocalDate: params.startLocalDate,
      startDate: params.startDate,
      endDate: params.endDate,
    });
  }
);

export const createWeeklyPlanApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/weeks" },
  async (params: ProjectLoopParams & CreateWeeklyPlanBody): Promise<WeeklyPlanDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createWeeklyPlanAuthorized(ctx, {
      projectId: params.projectId,
      cycleId: params.cycleId,
      weekNo: params.weekNo,
      focus: params.focus,
      mission: params.mission,
      startDate: params.startDate,
      endDate: params.endDate,
    });
  }
);

export const createWeeklyCommitmentApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/commitments" },
  async (params: ProjectLoopParams & CreateWeeklyCommitmentBody): Promise<WeeklyCommitmentDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createWeeklyCommitmentAuthorized(ctx, {
      projectId: params.projectId,
      weeklyPlanId: params.weeklyPlanId,
      title: params.title,
      initiativeId: params.initiativeId,
      plannedEffort: params.plannedEffort,
      ownerMemberId: params.ownerMemberId,
      purposeType: params.purposeType,
      purposeRef: params.purposeRef,
    });
  }
);

export const createTaskApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/tasks" },
  async (params: ProjectLoopParams & CreateTaskBody): Promise<TaskDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createTaskAuthorized(ctx, {
      projectId: params.projectId,
      title: params.title,
      weeklyCommitmentId: params.weeklyCommitmentId,
      initiativeId: params.initiativeId,
      priority: params.priority,
      plannedStartAt: params.plannedStartAt,
      dueAt: params.dueAt,
      status: params.status,
    });
  }
);

export const advanceTaskApi = api(
  { expose: true, method: "PATCH", path: "/operations/projects/:projectId/operating-loop/tasks/:taskId/status" },
  async (params: AdvanceTaskParams): Promise<TaskDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await verifyProjectInWorkspace(BigInt(ctx.workspaceId), BigInt(params.projectId));
    return advanceTaskService(ctx, {
      projectId: params.projectId,
      taskId: params.taskId,
      status: params.status,
    });
  }
);

export const advanceCycleWeekApi = api(
  { expose: true, method: "PATCH", path: "/operations/projects/:projectId/operating-loop/cycles/:cycleId/week" },
  async (params: AdvanceCycleWeekParams & AdvanceCycleWeekBody): Promise<AdvanceCycleWeekResultDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return advanceCycleWeekAuthorized(ctx, {
      projectId: params.projectId,
      cycleId: params.cycleId,
      expectedCurrentWeek: params.expectedCurrentWeek,
      reflection: params.reflection,
      executionScore: params.executionScore,
      outcomeScore: params.outcomeScore,
    });
  }
);
