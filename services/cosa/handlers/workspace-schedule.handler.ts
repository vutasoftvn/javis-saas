import { api, Header } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import * as scheduleSvc from "../services/workspace-schedule.service";
import { verifyPlatformToken, requireWorkerServiceAuth } from "../services/token.service";
import { db, schema } from "../models/db";

const { workspaceScheduleDefinitions, workspaceScheduleExecutions } = schema;

export interface CreateScheduleParams {
  authorization?: Header<"Authorization">;
  companyId: string;
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
  companyId: string;
  workspaceId: string;
}

export interface RunScheduleNowParams {
  authorization?: Header<"Authorization">;
  scheduleId: string;
  companyId: string;
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
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    const res = await scheduleSvc.createWorkspaceSchedule({
      companyId: params.companyId,
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
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    verifyPlatformToken(token);

    const items = await db
      .select()
      .from(workspaceScheduleDefinitions)
      .where(
        and(
          eq(workspaceScheduleDefinitions.companyId, params.companyId),
          eq(workspaceScheduleDefinitions.workspaceId, params.workspaceId)
        )
      )
      .orderBy(desc(workspaceScheduleDefinitions.createdAt));

    return { items, total: items.length };
  }
);

export const runScheduleNowEndpoint = api(
  { method: "POST", path: "/cosa/schedules/:scheduleId/run-now", expose: true },
  async (params: RunScheduleNowParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: params.scheduleId,
      companyId: params.companyId,
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

    const [execution] = await db
      .select()
      .from(workspaceScheduleExecutions)
      .where(eq(workspaceScheduleExecutions.id, params.executionId));

    if (!execution) {
      throw new Error("schedule execution not found");
    }
    return execution;
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
