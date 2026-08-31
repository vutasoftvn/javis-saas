import { api, Header } from "encore.dev/api";
import {
  TwelveWeekCycle,
  CreateTwelveWeekCycleRequest,
  WeeklyPlan,
  CreateWeeklyPlanRequest,
  WeeklyCommitment,
  CreateWeeklyCommitmentRequest,
  createCycleService,
  listCyclesService,
  createWeeklyPlanService,
  createWeeklyCommitmentService,
} from "../services/twelve-week-year.service";

export { TwelveWeekCycle, CreateTwelveWeekCycleRequest, WeeklyPlan, CreateWeeklyPlanRequest, WeeklyCommitment, CreateWeeklyCommitmentRequest };

// M1 §4 — bơm Authorization header vào request đi tới service (service tự
// requireWorkspaceAccess). Trước đây các endpoint này không xác thực gì.
type WithAuth<T> = Omit<T, "authorization"> & { authorization?: Header<"Authorization"> };

// ─── 12-Week Cycles Endpoints ───

export const createCycle = api(
  { expose: true, method: "POST", path: "/operations/cycles" },
  async (req: WithAuth<CreateTwelveWeekCycleRequest>): Promise<TwelveWeekCycle> => {
    return createCycleService(req);
  }
);

export const listCycles = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/cycles" },
  async (params: { workspaceId: string }): Promise<{ cycles: TwelveWeekCycle[] }> => {
    const cycles = await listCyclesService(params.workspaceId);
    return { cycles };
  }
);

// ─── Weekly Plans Endpoints ───

export const createWeeklyPlan = api(
  { expose: true, method: "POST", path: "/operations/weekly-plans" },
  async (req: WithAuth<CreateWeeklyPlanRequest>): Promise<WeeklyPlan> => {
    return createWeeklyPlanService(req);
  }
);

// ─── Weekly Commitments Endpoints ───

export const createWeeklyCommitment = api(
  { expose: true, method: "POST", path: "/operations/weekly-commitments" },
  async (req: WithAuth<CreateWeeklyCommitmentRequest>): Promise<WeeklyCommitment> => {
    return createWeeklyCommitmentService(req);
  }
);

// ─── Canonical MVP Endpoints ───

export const listTwelveWeekCycles = api(
  { expose: true, method: "GET", path: "/operations/twelve-week-cycles" },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }) => {
    const { listTwelveWeekCyclesService } = await import("../services/twelve-week-year.service");
    return listTwelveWeekCyclesService(workspaceId, authorization);
  }
);

export const listTwelveWeekPlans = api(
  { expose: true, method: "GET", path: "/operations/twelve-week-plans" },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }) => {
    const { listWeeklyPlansService } = await import("../services/twelve-week-year.service");
    return listWeeklyPlansService(workspaceId, authorization);
  }
);

export const listTwelveWeekCommitments = api(
  { expose: true, method: "GET", path: "/operations/twelve-week-commitments" },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }) => {
    const { listWeeklyCommitmentsService } = await import("../services/twelve-week-year.service");
    return listWeeklyCommitmentsService(workspaceId, authorization);
  }
);
