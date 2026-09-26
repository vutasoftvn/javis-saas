import { api, Header, Query } from "encore.dev/api";
import {
  createGoalService,
  getGoalTreeService,
  getGoalsNeedingReviewService,
  completeGoalService,
  createObjectiveService,
  addKeyResultService,
  updateKeyResultValueService,
  GoalType,
  GoalStatus,
} from "../services/goals.service";
import {
  listPendingReviewProjectsService,
  triageProjectService,
  ProjectTriageAction,
} from "../services/discovery-project.service";
import { requireWorkspaceAccess, requireWorkspaceWrite } from "../../shared/auth/workspace-access";

type WithAuth<T> = Omit<T, "authorization"> & { authorization?: Header<"Authorization"> };

export interface CreateGoalParams {
  workspaceId: string;
  parentId?: string;
  title: string;
  description?: string;
  goalType: GoalType;
  startDate?: string;
  endDate?: string;
  durationWeeks?: number;
  status?: GoalStatus;
  snapshotId?: string;
}

export interface CompleteGoalParams {
  id: string;
  workspaceId: string;
  forceCompleteActiveObjectives?: boolean;
}

export interface CreateCosaObjectiveParams {
  workspaceId: string;
  goalId: string;
  title: string;
  description?: string;
  ownerUserId?: string;
  weight?: number;
  displayOrder?: number;
}

export interface AddCosaKeyResultParams {
  id: string; // objectiveId
  workspaceId: string;
  metricName: string;
  baseline?: number;
  target: number;
  unit?: string;
  displayOrder?: number;
}

export interface CheckinKeyResultParams {
  id: string; // keyResultId
  workspaceId: string;
  currentValue: number;
}

export interface TriageProjectParams {
  workspaceId: string;
  projectId: string;
  action: ProjectTriageAction;
  targetObjectiveId?: string;
  newGoalId?: string;
  newObjectiveTitle?: string;
}

export const createGoal = api(
  { method: "POST", path: "/operations/goals", expose: true },
  async (params: WithAuth<CreateGoalParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return createGoalService(input);
  }
);

export const getGoalTree = api(
  { method: "GET", path: "/operations/goals/tree", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getGoalTreeService(params.workspaceId);
  }
);

export const getGoalsNeedingReview = api(
  { method: "GET", path: "/operations/goals/needing-review", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getGoalsNeedingReviewService(params.workspaceId);
  }
);

export const completeGoal = api(
  { method: "POST", path: "/operations/goals/:id/complete", expose: true },
  async (params: WithAuth<CompleteGoalParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    return completeGoalService({
      workspaceId: params.workspaceId,
      goalId: params.id,
      forceCompleteActiveObjectives: params.forceCompleteActiveObjectives,
    });
  }
);

export const createCosaObjective = api(
  { method: "POST", path: "/operations/cosa/objectives", expose: true },
  async (params: WithAuth<CreateCosaObjectiveParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return createObjectiveService(input);
  }
);

export const addCosaKeyResult = api(
  { method: "POST", path: "/operations/cosa/objectives/:id/key-results", expose: true },
  async (params: WithAuth<AddCosaKeyResultParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    return addKeyResultService({
      workspaceId: params.workspaceId,
      objectiveId: params.id,
      metricName: params.metricName,
      baseline: params.baseline,
      target: params.target,
      unit: params.unit,
      displayOrder: params.displayOrder,
    });
  }
);

export const checkinCosaKeyResult = api(
  { method: "POST", path: "/operations/cosa/key-results/:id/checkin", expose: true },
  async (params: WithAuth<CheckinKeyResultParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    return updateKeyResultValueService({
      workspaceId: params.workspaceId,
      keyResultId: params.id,
      currentValue: params.currentValue,
    });
  }
);

export const listPendingReviewProjects = api(
  { method: "GET", path: "/operations/projects/pending-review", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listPendingReviewProjectsService(params.workspaceId);
  }
);

export const triageProject = api(
  { method: "POST", path: "/operations/projects/triage", expose: true },
  async (params: WithAuth<TriageProjectParams>) => {
    await requireWorkspaceWrite(params.authorization, params.workspaceId);
    const { authorization: _auth, ...input } = params;
    return triageProjectService(input);
  }
);
