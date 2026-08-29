import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { taskExecutionRecords, tasks } = schema;

export interface TaskExecutionRecordView {
  id: string;
  workspaceId: string;
  taskId: string;
  runId: string | null;
  toolCallId: string | null;
  capabilityId: string;
  triggeredByKind: string;
  decisionRecordId: string | null;
  status: "SUCCESS" | "FAILED";
  errorDetails: any;
  createdAt: string;
}

export async function recordTaskExecutionService(p: {
  workspaceId: bigint;
  taskId: bigint;
  runId?: string;
  toolCallId?: string;
  capabilityId: string;
  triggeredByKind: "agent" | "founder" | "workflow" | "system";
  decisionRecordId?: bigint;
  status?: "SUCCESS" | "FAILED";
  errorDetails?: any;
}): Promise<TaskExecutionRecordView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(taskExecutionRecords)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      taskId: p.taskId,
      runId: p.runId ?? null,
      toolCallId: p.toolCallId ?? null,
      capabilityId: p.capabilityId,
      triggeredByKind: p.triggeredByKind,
      decisionRecordId: p.decisionRecordId ?? null,
      status: p.status ?? "SUCCESS",
      errorDetails: p.errorDetails ?? null,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    taskId: String(created.taskId),
    runId: created.runId,
    toolCallId: created.toolCallId,
    capabilityId: created.capabilityId,
    triggeredByKind: created.triggeredByKind,
    decisionRecordId: created.decisionRecordId ? String(created.decisionRecordId) : null,
    status: created.status as any,
    errorDetails: created.errorDetails,
    createdAt: created.createdAt.toISOString(),
  };
}
