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
  metricName: string;
  baseline?: number;
  target: number;
  unit?: string;
  displayOrder?: number;
}

export interface CheckinKeyResultParams {
  id: string; // keyResultId
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
    return createGoalService(params);
  }
);

export const getGoalTree = api(
  { method: "GET", path: "/operations/goals/tree", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    return getGoalTreeService(params.workspaceId);
  }
);

export const getGoalsNeedingReview = api(
  { method: "GET", path: "/operations/goals/needing-review", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    return getGoalsNeedingReviewService(params.workspaceId);
  }
);

export const completeGoal = api(
  { method: "POST", path: "/operations/goals/:id/complete", expose: true },
  async (params: WithAuth<CompleteGoalParams>) => {
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
    return createObjectiveService(params);
  }
);

export const addCosaKeyResult = api(
  { method: "POST", path: "/operations/cosa/objectives/:id/key-results", expose: true },
  async (params: WithAuth<AddCosaKeyResultParams>) => {
    return addKeyResultService({
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
    return updateKeyResultValueService({
      keyResultId: params.id,
      currentValue: params.currentValue,
    });
  }
);

export const listPendingReviewProjects = api(
  { method: "GET", path: "/operations/projects/pending-review", expose: true },
  async (params: WithAuth<{ workspaceId: Query<string> }>) => {
    return listPendingReviewProjectsService(params.workspaceId);
  }
);

export const triageProject = api(
  { method: "POST", path: "/operations/projects/triage", expose: true },
  async (params: WithAuth<TriageProjectParams>) => {
    return triageProjectService(params);
  }
);
