import { api, Header } from "encore.dev/api";
import * as scheduleSvc from "../services/workspace-schedule.service";
import { resolveCallerAuthorizedForWorkspace } from "../services/workspace-connector.service";
import { requireWorkerServiceAuth } from "../services/token.service";

// Encore.ts (phân tích static AST lúc compile để sinh response schema) chỉ
// chấp nhận response type là `interface` phẳng — KHÔNG chấp nhận type alias
// suy ra từ generic như `typeof table.$inferSelect` (`ScheduleDefinitionRow`/
// `ScheduleExecutionRow` ở `schedule.repository.ts`), lỗi hard lúc `encore
// test --prepare`/`encore run`: "expected named interface type". Do đó khai
// báo lại đúng field set (camelCase, khớp cột Drizzle ở
// `storage/control-plane-schema.ts`) làm interface độc lập chỉ để mô tả
// response — value trả về từ `repo.insertScheduleDefinition`/... vẫn khớp
// cấu trúc nhờ TypeScript structural typing.
export interface ScheduleDefinitionResponse {
  id: string;
  organizationId: string;
  createdBy: string;
  scheduleKind: string;
  timezone: string;
  runAt: Date | null;
  hour: number | null;
  minute: number | null;
  weekdays: unknown;
  promptTemplate: string;
  agentProfile: string;
  projectId: string | null;
  isLegacyUnscoped: boolean;
  connectorGrantIds: unknown;
  state: string;
  nextRunAt: Date | null;
  lastRunAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface ScheduleExecutionResponse {
  id: string;
  definitionId: string;
  organizationId: string;
  scheduledFor: Date;
  promptTemplateSnapshot: string;
  agentProfileSnapshot: string;
  projectIdSnapshot: string | null;
  connectorGrantIdsSnapshot: unknown;
  state: string;
  taskId: string | null;
  conversationId: string | null;
  runId: string | null;
  error: string | null;
  attemptCount: number;
  nextAttemptAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateScheduleParams {
  authorization?: Header<"Authorization">;
  organizationId: string;
  projectId: string;
  scheduleKind: scheduleSvc.ScheduleKind;
  timezone?: string;
  runAt?: string;
  hour?: number;
  minute?: number;
  weekdays?: number[];
  promptTemplate: string;
  agentProfile?: string;
  connectorGrantIds?: string[];
}

export interface ListSchedulesParams {
  authorization?: Header<"Authorization">;
  organizationId: string;
}

export interface RunScheduleNowParams {
  authorization?: Header<"Authorization">;
  scheduleId: string;
  organizationId: string;
}

export interface CompleteExecutionParams {
  authorization?: Header<"Authorization">;
  executionId: string;
  state: scheduleSvc.ScheduleExecutionState;
  conversationId?: string;
  runId?: string;
  error?: string;
}

export const createScheduleEndpoint = api(
  { method: "POST", path: "/cosa/schedules", expose: true },
  // Bug thật phát hiện qua E2E S10 (2026-09-14 schedule-project-scope, Task
  // 8): thiếu annotation `Promise<T>` tường minh khiến Encore.ts (phân tích
  // static AST lúc compile) không suy được response schema -> handler tính
  // đúng giá trị trả về nhưng HTTP response thật sự đi ra ngoài luôn
  // content-length=0/body rỗng (unit test gọi thẳng hàm nên không bắt được,
  // chỉ lộ khi có tiến trình Encore thật + HTTP client thật parse JSON).
  // Áp dụng cho toàn bộ 5 endpoint trong file này để nhất quán với pattern đã
  // dùng ở `control-plane.handler.ts`.
  async (params: CreateScheduleParams): Promise<ScheduleDefinitionResponse> => {
    // B5 fix — resolveCallerAuthorizedForWorkspace ưu tiên control-plane
    // delegation (apps/cosa đã cross-check membership thật), fallback
    // platform token + verifyWorkspaceMembership (hành vi cũ) — xem
    // workspace-connector.service.ts.
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.organizationId);

    const res = await scheduleSvc.createWorkspaceSchedule({
      organizationId: params.organizationId,
      createdBy: caller.sub,
      scheduleKind: params.scheduleKind,
      timezone: params.timezone,
      runAt: params.runAt ? new Date(params.runAt) : null,
      hour: params.hour,
      minute: params.minute,
      weekdays: params.weekdays,
      promptTemplate: params.promptTemplate,
      agentProfile: params.agentProfile,
      connectorGrantIds: params.connectorGrantIds,
      projectId: params.projectId,
    });
    return res;
  }
);

export const listSchedulesEndpoint = api(
  { method: "GET", path: "/cosa/schedules", expose: true },
  async (
    params: ListSchedulesParams
  ): Promise<{ items: ScheduleDefinitionResponse[]; total: number }> => {
    await resolveCallerAuthorizedForWorkspace(params.authorization, params.organizationId);
    const list = await scheduleSvc.listWorkspaceSchedules(params.organizationId);
    return { items: list.items, total: list.total };
  }
);

export const runScheduleNowEndpoint = api(
  { method: "POST", path: "/cosa/schedules/:scheduleId/run-now", expose: true },
  async (params: RunScheduleNowParams): Promise<ScheduleExecutionResponse> => {
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.organizationId);

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: params.scheduleId,
      organizationId: params.organizationId,
      principalId: caller.sub,
    });
    return execution;
  }
);

export const getScheduleExecutionEndpoint = api(
  { method: "GET", path: "/cosa/schedules/executions/:executionId", expose: true },
  async (params: {
    authorization?: Header<"Authorization">;
    executionId: string;
  }): Promise<ScheduleExecutionResponse> => {
    // Internal worker authentication
    requireWorkerServiceAuth(params.authorization);

    return await scheduleSvc.getScheduleExecution(params.executionId);
  }
);

export const completeScheduleExecutionEndpoint = api(
  { method: "POST", path: "/cosa/schedules/executions/complete", expose: true },
  async (params: CompleteExecutionParams): Promise<{ ok: boolean }> => {
    requireWorkerServiceAuth(params.authorization);

    const res = await scheduleSvc.completeScheduleExecution({
      executionId: params.executionId,
      state: params.state,
      conversationId: params.conversationId,
      runId: params.runId,
      error: params.error,
    });
    return { ok: !!res };
  }
);
