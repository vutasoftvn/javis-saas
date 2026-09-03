import { api, Header } from "encore.dev/api";
import * as scheduleSvc from "../services/workspace-schedule.service";
import { resolveCallerAuthorizedForWorkspace } from "../services/workspace-connector.service";
import { requireWorkerServiceAuth } from "../services/token.service";

export interface CreateScheduleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
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
  workspaceId: string;
}

export interface RunScheduleNowParams {
  authorization?: Header<"Authorization">;
  scheduleId: string;
  workspaceId: string;
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
  async (params: CreateScheduleParams) => {
    // B5 fix — resolveCallerAuthorizedForWorkspace ưu tiên control-plane
    // delegation (apps/cosa đã cross-check membership thật), fallback
    // platform token + verifyWorkspaceMembership (hành vi cũ) — xem
    // workspace-connector.service.ts.
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.workspaceId);

    const res = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: params.workspaceId,
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
    });
    return res;
  }
);

export const listSchedulesEndpoint = api(
  { method: "GET", path: "/cosa/schedules", expose: true },
  async (params: ListSchedulesParams) => {
    await resolveCallerAuthorizedForWorkspace(params.authorization, params.workspaceId);
    return scheduleSvc.listWorkspaceSchedules(params.workspaceId);
  }
);

export const runScheduleNowEndpoint = api(
  { method: "POST", path: "/cosa/schedules/:scheduleId/run-now", expose: true },
  async (params: RunScheduleNowParams) => {
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.workspaceId);

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: params.scheduleId,
      workspaceId: params.workspaceId,
      principalId: caller.sub,
    });
    return execution;
  }
);

export const getScheduleExecutionEndpoint = api(
  { method: "GET", path: "/cosa/schedules/executions/:executionId", expose: true },
  async (params: { authorization?: Header<"Authorization">; executionId: string }) => {
    // Internal worker authentication
    requireWorkerServiceAuth(params.authorization);

    return scheduleSvc.getScheduleExecution(params.executionId);
  }
);

export const completeScheduleExecutionEndpoint = api(
  { method: "POST", path: "/cosa/schedules/executions/complete", expose: true },
  async (params: CompleteExecutionParams) => {
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
