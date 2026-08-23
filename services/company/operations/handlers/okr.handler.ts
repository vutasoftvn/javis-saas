import { api } from "encore.dev/api";
import {
  OkrCycle,
  CreateOkrCycleParams,
  Objective,
  CreateObjectiveParams,
  KeyResult,
  AddKeyResultParams,
  ObjectiveProgress,
  createOkrCycleService,
  createObjectiveService,
  addKeyResultService,
  checkinService,
  getObjectiveProgressService,
} from "../services/okr.service";

export { OkrCycle, CreateOkrCycleParams, Objective, CreateObjectiveParams, KeyResult, AddKeyResultParams };

export const createOkrCycle = api(
  { method: "POST", path: "/operations/okr-cycles", expose: true },
  async (params: CreateOkrCycleParams): Promise<OkrCycle> => {
    return createOkrCycleService(params);
  }
);

export const createObjective = api(
  { method: "POST", path: "/operations/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    return createObjectiveService(params);
  }
);

export const addKeyResult = api(
  { method: "POST", path: "/operations/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    return addKeyResultService(params);
  }
);

export const checkin = api(
  { method: "POST", path: "/operations/key-results/:id/checkin", expose: true },
  async ({ id, value }: { id: string; value: number }): Promise<KeyResult> => {
    return checkinService(id, value);
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/operations/objectives/:objectiveId/progress", expose: true },
  async ({ objectiveId }: { objectiveId: string }): Promise<ObjectiveProgress> => {
    return getObjectiveProgressService(objectiveId);
  }
);
