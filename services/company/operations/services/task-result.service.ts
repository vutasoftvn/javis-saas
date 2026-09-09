import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const {
  taskResults,
  outcomeAnalysisRequests,
  outcomeAssessments,
  taskOutcomeContracts,
  tasks,
} = schema;

export type AnalysisPolicy = "AUTO_ALL_TASKS" | "AUTO_BY_RULE" | "MANUAL";
export type AnalysisKind = "TASK_OUTCOME" | "PROJECT_OUTCOME_SYNTHESIS";

export const OPERATING_TASK_RESULT_SUBMITTED_V1 = "operating.task.result_submitted.v1";

export interface TaskResultView {
  id: string;
  taskId: string;
  contractId: string;
  revision: number;
  summary: string;
  artifactRefs: string[];
  evidenceRefs: string[];
  claimedMeasurements: Record<string, number | string>;
  createdAt: string;
}

export interface SubmitTaskResultInput {
  taskId: string;
  contractId: string;
  workAttemptIds: string[];
  summary: string;
  artifactRefs: string[];
  evidenceRefs: string[];
  claimedMeasurements: Record<string, number | string>;
  structuredOutputs?: Record<string, unknown>;
  blockers?: string[];
  submittedByKind?: "agent" | "human" | "system";
  submittedById?: string;
  idempotencyKey: string;
}

function toView(row: typeof taskResults.$inferSelect): TaskResultView {
  return {
    id: row.id.toString(),
    taskId: row.taskId.toString(),
    contractId: row.contractId.toString(),
    revision: row.resultRevision,
    summary: row.summary,
    artifactRefs: Array.isArray(row.artifactRefs) ? (row.artifactRefs as string[]) : [],
    evidenceRefs: Array.isArray(row.evidenceRefs) ? (row.evidenceRefs as string[]) : [],
    claimedMeasurements: (row.claimedMeasurements ?? {}) as Record<string, number | string>,
    createdAt: row.createdAt.toISOString(),
  };
}

/**
 * Policy phân tích của workspace. Task 7A thay bằng bảng versioned do founder
 * quản trị; slice này mặc định AUTO_ALL_TASKS (spec §7 decision 7).
 */
export async function getAnalysisPolicy(_workspaceId: string): Promise<AnalysisPolicy> {
  return "AUTO_ALL_TASKS";
}

/**
 * Nộp Task Result theo revision (append-only). AUTO_ALL_TASKS tạo đúng một
 * OutcomeAnalysisRequest cho mỗi result revision hợp lệ, trong cùng
 * transaction. KHÔNG cập nhật task.status hay KR.actualValue ở bất kỳ nhánh
 * nào. Revision mới đánh SUPERSEDED assessment cũ (không xóa).
 */
export async function submitTaskResult(
  input: SubmitTaskResultInput,
  ctx: TenantContext
): Promise<TaskResultView> {
  const wsId = BigInt(ctx.workspaceId);

  if (!input.summary?.trim()) throw APIError.invalidArgument("summary is required");

  // Idempotency — trả về bản gốc.
  if (input.idempotencyKey) {
    const [existing] = await db
      .select()
      .from(taskResults)
      .where(
        and(eq(taskResults.workspaceId, wsId), eq(taskResults.idempotencyKey, input.idempotencyKey))
      )
      .limit(1);
    if (existing) return toView(existing);
  }

  // Verify task + current CONFIRMED contract.
  const [task] = await db
    .select({ id: tasks.id, activeOutcomeContractId: tasks.activeOutcomeContractId })
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(input.taskId)), eq(tasks.workspaceId, wsId)))
    .limit(1);
  if (!task) throw APIError.notFound(`task ${input.taskId} not found in workspace`);

  const [contract] = await db
    .select({
      id: taskOutcomeContracts.id,
      status: taskOutcomeContracts.status,
      revision: taskOutcomeContracts.revision,
      taskId: taskOutcomeContracts.taskId,
    })
    .from(taskOutcomeContracts)
    .where(
      and(
        eq(taskOutcomeContracts.id, BigInt(input.contractId)),
        eq(taskOutcomeContracts.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!contract || contract.taskId.toString() !== input.taskId) {
    throw APIError.invalidArgument("contractId is not this task's contract in this workspace");
  }
  if (contract.status !== "CONFIRMED") {
    throw APIError.failedPrecondition(`outcome contract is ${contract.status}, not CONFIRMED`);
  }
  if (
    task.activeOutcomeContractId &&
    task.activeOutcomeContractId.toString() !== input.contractId
  ) {
    throw APIError.failedPrecondition("result must reference the task's active confirmed contract");
  }

  const policy = await getAnalysisPolicy(ctx.workspaceId);
  const actor = { kind: (input.submittedByKind ?? "agent") as "user" | "agent" | "system", id: input.submittedById || "0" };

  return db.transaction(async (tx) => {
    const [prev] = await tx
      .select({ resultRevision: taskResults.resultRevision })
      .from(taskResults)
      .where(eq(taskResults.taskId, BigInt(input.taskId)))
      .orderBy(desc(taskResults.resultRevision))
      .limit(1);
    const revision = (prev?.resultRevision ?? 0) + 1;

    const [row] = await tx
      .insert(taskResults)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        taskId: BigInt(input.taskId),
        contractId: BigInt(input.contractId),
        resultRevision: revision,
        submittedByKind: input.submittedByKind ?? "agent",
        submittedById: input.submittedById ?? null,
        workAttemptIds: input.workAttemptIds ?? [],
        summary: input.summary,
        structuredOutputs: input.structuredOutputs ?? {},
        artifactRefs: input.artifactRefs ?? [],
        evidenceRefs: input.evidenceRefs ?? [],
        claimedMeasurements: input.claimedMeasurements ?? {},
        blockers: input.blockers ?? [],
        idempotencyKey: input.idempotencyKey ?? null,
      })
      .returning();
    if (!row) throw APIError.internal("failed to create task result");

    // Revision mới -> assessment cũ (mọi request trước của task này) SUPERSEDED.
    if (revision > 1) {
      const priorResultIds = (
        await tx
          .select({ id: taskResults.id })
          .from(taskResults)
          .where(
            and(eq(taskResults.taskId, BigInt(input.taskId)), eq(taskResults.workspaceId, wsId))
          )
      )
        .map((r) => r.id)
        .filter((id) => id !== row.id);
      if (priorResultIds.length > 0) {
        for (const pid of priorResultIds) {
          await tx
            .update(outcomeAssessments)
            .set({ status: "SUPERSEDED" })
            .where(
              and(
                eq(outcomeAssessments.taskResultId, pid),
                eq(outcomeAssessments.status, "READY")
              )
            );
        }
      }
    }

    // AUTO_ALL_TASKS -> tạo đúng một request (idempotent theo unique index).
    if (policy === "AUTO_ALL_TASKS") {
      await tx
        .insert(outcomeAnalysisRequests)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          taskResultId: row.id,
          contractId: BigInt(input.contractId),
          contractRevision: contract.revision,
          analysisKind: "TASK_OUTCOME",
          analysisPolicy: policy,
          status: "QUEUED",
        })
        .onConflictDoNothing();
    }
    // AUTO_BY_RULE / MANUAL: chưa tạo request tự động (Task 7A / lệnh manual).

    await appendOutboxEvent(
      tx,
      makeBusinessEvent({
        eventType: OPERATING_TASK_RESULT_SUBMITTED_V1,
        workspaceId: ctx.workspaceId,
        aggregateType: "task_result",
        aggregateId: row.id.toString(),
        correlationId: ctx.correlationId || generateSnowflake().toString(),
        actor,
        classification: "internal",
        payload: {
          workspaceId: ctx.workspaceId,
          taskId: input.taskId,
          taskResultId: row.id.toString(),
          contractId: input.contractId,
          contractRevision: contract.revision,
          resultRevision: revision,
          analysisPolicy: policy,
        },
      })
    );

    return toView(row);
  });
}

export async function listOutcomeAnalysisRequests(
  taskResultId: string,
  ctx: TenantContext
): Promise<Array<{ id: string; status: string; analysisKind: string; contractRevision: number }>> {
  const rows = await db
    .select()
    .from(outcomeAnalysisRequests)
    .where(
      and(
        eq(outcomeAnalysisRequests.taskResultId, BigInt(taskResultId)),
        eq(outcomeAnalysisRequests.workspaceId, BigInt(ctx.workspaceId))
      )
    );
  return rows.map((r) => ({
    id: r.id.toString(),
    status: r.status,
    analysisKind: r.analysisKind,
    contractRevision: r.contractRevision,
  }));
}
