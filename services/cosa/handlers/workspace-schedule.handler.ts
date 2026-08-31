import { api, Header, APIError } from "encore.dev/api";
import * as scheduleSvc from "../services/workspace-schedule.service";
import * as connectorSvc from "../services/workspace-connector.service";
import { verifyPlatformToken, requireWorkerServiceAuth } from "../services/token.service";

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
    if (!params.authorization) throw APIError.unauthenticated("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const res = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: params.workspaceId,
      createdBy: claims.sub,
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
    if (!params.authorization) throw APIError.unauthenticated("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    return scheduleSvc.listWorkspaceSchedules(params.workspaceId);
  }
);

export const runScheduleNowEndpoint = api(
  { method: "POST", path: "/cosa/schedules/:scheduleId/run-now", expose: true },
  async (params: RunScheduleNowParams) => {
    if (!params.authorization) throw APIError.unauthenticated("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: params.scheduleId,
      workspaceId: params.workspaceId,
      principalId: claims.sub,
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
