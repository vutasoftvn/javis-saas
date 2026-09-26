import { api, APIError, Header } from "encore.dev/api";
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
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

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
  async (params: {
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<{ cycles: TwelveWeekCycle[] }> => {
    // Trước đây endpoint này không xác thực: ai cũng đọc được cycle của workspace bất kỳ.
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const cycles = await listCyclesService(params.workspaceId);
    return { cycles };
  }
);

export const updateCycle = api(
  { expose: true, method: "PATCH", path: "/operations/cycles/:id" },
  async ({
    id,
    authorization,
    workspaceId,
    expectedVersion,
    displayName,
    theme,
    visionStatement,
    durationWeeks,
    startLocalDate,
    timezone,
    status,
    reason,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
    expectedVersion?: number;
    displayName?: string | null;
    theme?: string | null;
    visionStatement?: string;
    durationWeeks?: number;
    startLocalDate?: string | null;
    timezone?: string | null;
    status?: string;
    reason?: string | null;
  }): Promise<TwelveWeekCycle> => {
    // Founder Trial R1 — resize độ dài Operating Cycle đang chạy hiện KHÔNG
    // được hỗ trợ (không có route project-scoped thay thế nào tồn tại trong
    // codebase). Endpoint generic này không nhận `durationWeeks` từ client.
    if (durationWeeks !== undefined) {
      throw APIError.invalidArgument(
        "Resizing an in-progress operating cycle is not supported. Complete or cancel the current cycle, then create a new one with the desired duration."
      );
    }
    const { updateCycleService } = await import("../services/twelve-week-year.service");
    return updateCycleService({
      workspaceId,
      cycleId: id,
      authorization,
      expectedVersion,
      displayName,
      theme,
      visionStatement,
      durationWeeks,
      startLocalDate,
      timezone,
      status,
      reason,
    });
  }
);

// ─── Weekly Plans Endpoints ───

export const createWeeklyPlan = api(
  { expose: true, method: "POST", path: "/operations/weekly-plans" },
  async (req: WithAuth<CreateWeeklyPlanRequest>): Promise<WeeklyPlan> => {
    return createWeeklyPlanService(req);
  }
);

export const updateWeeklyPlan = api(
  { expose: true, method: "PATCH", path: "/operations/twelve-week-plans/:id" },
  async ({
    id,
    authorization,
    workspaceId,
    executionScore,
    outcomeScore,
    reflection,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
    executionScore?: number | null;
    outcomeScore?: number | null;
    reflection?: string | null;
  }): Promise<WeeklyPlan> => {
    const { updateWeeklyPlanService } = await import("../services/twelve-week-year.service");
    return updateWeeklyPlanService(id, {
      workspaceId,
      authorization,
      executionScore,
      outcomeScore,
      reflection,
    });
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
