import { APIError } from "encore.dev/api";
import { and, asc, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import {
  OPERATING_WORK_PACKAGE_QUEUED_V1,
  OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1,
} from "../../shared/events/event-types";
import {
  EligibilityFacts,
  assertEmployeeEligible,
} from "./workforce-eligibility.client";
import {
  CreateTaskOutcomeContractInput,
  Tx,
  assertTaskCanEnterQueue,
  insertContractRevision,
} from "./task-outcome-contract.service";

const { taskWorkPackages, workPackageAttempts, workPackageEvents, tasks, taskOutcomeContracts } =
  schema;

export type WorkPackageStatus =
  | "QUEUED"
  | "LEASED"
  | "RUNNING"
  | "VALIDATION_PASSED"
  | "PENDING_MANAGER_REVIEW"
  | "ESCALATED_TO_FOUNDER"
  | "ACCEPTED"
  | "REWORK"
  | "REJECTED"
  | "BLOCKED"
  | "ON_HOLD"
  | "CANCELLED";

export type Priority = "P0" | "P1" | "P2" | "P3";
const PRIORITIES: readonly Priority[] = ["P0", "P1", "P2", "P3"];

// Trạng thái attempt được coi là "đang giữ lease/đang chạy" — reassign lúc này
// chỉ ghi reassignment_requested, không đóng attempt ngay (spec §7).
const LEASED_WP_STATUSES: readonly WorkPackageStatus[] = ["LEASED", "RUNNING"];

// Rollout flag (spec §14). Khi TẮT (mặc định): giữ hành vi Task 2, không gọi
// Control Plane, attempt không có snapshot. Khi BẬT: fail-closed eligibility
// check trước mọi attempt (Task 3). Pilot bật flag sau khi E2E xanh.
function eligibilityEnabled(): boolean {
  return process.env.AI_WORKFORCE_V2_ENABLED === "true";
}

async function checkEligibility(
  ctx: TenantContext,
  agentInstanceId: string
): Promise<EligibilityFacts | null> {
  if (!eligibilityEnabled()) return null;
  return assertEmployeeEligible({
    workspaceId: ctx.workspaceId,
    agentInstanceId,
    requiredCapabilityRefs: [],
    correlationId: ctx.correlationId,
  });
}

export interface WorkPackageView {
  workPackageId: string;
  workspaceId: string;
  taskId: string;
  outcomeContractId: string;
  objective: string;
  outputContract: Record<string, unknown>;
  acceptanceRubric: Record<string, number>;
  assignedAgentInstanceId: string;
  requestedPriority: Priority;
  effectivePriority: Priority;
  priorityReason: string | null;
  status: WorkPackageStatus;
  dependencyIds: string[];
  version: number;
  queuedAt: string;
  createdAt: string;
}

export interface AttemptView {
  attemptId: string;
  workPackageId: string;
  sequenceNo: number;
  assignedAgentInstanceId: string;
  runId: string | null;
  status: string;
  startedAt: string;
  endedAt: string | null;
  endedReason: string | null;
}

function toWpView(row: typeof taskWorkPackages.$inferSelect): WorkPackageView {
  return {
    workPackageId: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    taskId: row.taskId.toString(),
    outcomeContractId: row.outcomeContractId.toString(),
    objective: row.objective,
    outputContract: (row.outputContract ?? {}) as Record<string, unknown>,
    acceptanceRubric: (row.acceptanceRubric ?? {}) as Record<string, number>,
    assignedAgentInstanceId: row.assignedAgentInstanceId,
    requestedPriority: row.requestedPriority as Priority,
    effectivePriority: row.effectivePriority as Priority,
    priorityReason: row.priorityReason ?? null,
    status: row.status as WorkPackageStatus,
    dependencyIds: Array.isArray(row.dependencyIds) ? (row.dependencyIds as string[]) : [],
    version: row.version,
    queuedAt: row.queuedAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
  };
}

function toAttemptView(row: typeof workPackageAttempts.$inferSelect): AttemptView {
  return {
    attemptId: row.id.toString(),
    workPackageId: row.workPackageId.toString(),
    sequenceNo: row.sequenceNo,
    assignedAgentInstanceId: row.assignedAgentInstanceId,
    runId: row.runId ?? null,
    status: row.status,
    startedAt: row.startedAt.toISOString(),
    endedAt: row.endedAt ? row.endedAt.toISOString() : null,
    endedReason: row.endedReason ?? null,
  };
}

async function appendWpEvent(
  tx: Tx,
  input: {
    workspaceId: string;
    workPackageId: string;
    eventType: string;
    actor: { kind: string; id?: string };
    before?: unknown;
    after?: unknown;
    reason?: string;
    correlationId?: string;
  }
): Promise<void> {
  await tx.insert(workPackageEvents).values({
    id: generateSnowflake(),
    workspaceId: BigInt(input.workspaceId),
    workPackageId: BigInt(input.workPackageId),
    eventType: input.eventType,
    actorKind: input.actor.kind,
    actorId: input.actor.id ?? null,
    beforeJson: input.before ?? null,
    afterJson: input.after ?? null,
    reason: input.reason ?? null,
    correlationId: input.correlationId ?? null,
  });
}

/**
 * Mở một attempt mới cho package. Ném lỗi nếu package đã có attempt đang mở
 * (ended_at IS NULL) — enforce "không hai active attempt" (spec §7). Partial
 * unique index là hàng rào cuối; đây là check tường minh cho thông báo rõ.
 */
export async function openAttempt(
  tx: Tx,
  input: {
    workspaceId: string;
    workPackageId: string;
    assignedAgentInstanceId: string;
    sequenceNo?: number;
    assignmentSnapshot?: Record<string, unknown> | null;
    specSnapshot?: Record<string, unknown> | null;
  }
): Promise<AttemptView> {
  const wsId = BigInt(input.workspaceId);
  const wpId = BigInt(input.workPackageId);

  const [active] = await tx
    .select({ id: workPackageAttempts.id })
    .from(workPackageAttempts)
    .where(and(eq(workPackageAttempts.workPackageId, wpId), isNull(workPackageAttempts.endedAt)))
    .limit(1);
  if (active) {
    throw APIError.failedPrecondition("work package already has an active attempt");
  }

  let seq = input.sequenceNo;
  if (seq === undefined) {
    const [last] = await tx
      .select({ sequenceNo: workPackageAttempts.sequenceNo })
      .from(workPackageAttempts)
      .where(eq(workPackageAttempts.workPackageId, wpId))
      .orderBy(asc(workPackageAttempts.sequenceNo));
    seq = (last?.sequenceNo ?? 0) + 1;
  }

  const [row] = await tx
    .insert(workPackageAttempts)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      workPackageId: wpId,
      sequenceNo: seq,
      assignedAgentInstanceId: input.assignedAgentInstanceId,
      assignmentSnapshot: input.assignmentSnapshot ?? null,
      specSnapshot: input.specSnapshot ?? null,
      status: "ACTIVE",
    })
    .returning();
  if (!row) throw APIError.internal("failed to open attempt");
  return toAttemptView(row);
}

function validatePackageShape(input: {
  requestedPriority: string;
  objective: string;
  outputContract: Record<string, unknown>;
  acceptanceRubric: Record<string, number>;
  assignedAgentInstanceId: string;
}): void {
  if (!PRIORITIES.includes(input.requestedPriority as Priority)) {
    throw APIError.invalidArgument(`requestedPriority must be one of ${PRIORITIES.join(", ")}`);
  }
  if (!input.objective?.trim()) {
    throw APIError.invalidArgument("objective is required");
  }
  if (!input.assignedAgentInstanceId?.trim()) {
    throw APIError.invalidArgument("assignedAgentInstanceId is required");
  }
  if (!input.outputContract || Object.keys(input.outputContract).length === 0) {
    throw APIError.invalidArgument("outputContract is required");
  }
  if (!input.acceptanceRubric || Object.keys(input.acceptanceRubric).length === 0) {
    throw APIError.invalidArgument("acceptanceRubric is required");
  }
}

async function idempotentHit(
  wsId: bigint,
  idempotencyKey: string
): Promise<WorkPackageView | null> {
  const [existing] = await db
    .select()
    .from(taskWorkPackages)
    .where(
      and(
        eq(taskWorkPackages.workspaceId, wsId),
        eq(taskWorkPackages.idempotencyKey, idempotencyKey)
      )
    )
    .limit(1);
  return existing ? toWpView(existing) : null;
}

async function insertQueuedPackage(
  tx: Tx,
  input: {
    workspaceId: string;
    taskId: string;
    outcomeContractId: string;
    assignedAgentInstanceId: string;
    requestedPriority: Priority;
    objective: string;
    outputContract: Record<string, unknown>;
    acceptanceRubric: Record<string, number>;
    idempotencyKey?: string;
    requestedByManagerId?: string;
    actor: { kind: string; id?: string };
    eligibility?: EligibilityFacts | null;
    correlationId?: string;
  }
): Promise<{ wp: WorkPackageView; attempt: AttemptView }> {
  const [row] = await tx
    .insert(taskWorkPackages)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(input.workspaceId),
      taskId: BigInt(input.taskId),
      outcomeContractId: BigInt(input.outcomeContractId),
      objective: input.objective,
      outputContract: input.outputContract,
      acceptanceRubric: input.acceptanceRubric,
      requestedByManagerId: input.requestedByManagerId
        ? BigInt(input.requestedByManagerId)
        : null,
      assignedAgentInstanceId: input.assignedAgentInstanceId,
      requestedPriority: input.requestedPriority,
      effectivePriority: input.requestedPriority,
      status: "QUEUED",
      idempotencyKey: input.idempotencyKey ?? null,
    })
    .returning();
  if (!row) throw APIError.internal("failed to create work package");
  const wp = toWpView(row);

  const attempt = await openAttempt(tx, {
    workspaceId: input.workspaceId,
    workPackageId: wp.workPackageId,
    assignedAgentInstanceId: input.assignedAgentInstanceId,
    sequenceNo: 1,
    assignmentSnapshot: input.eligibility
      ? { assignmentId: input.eligibility.assignmentId }
      : null,
    specSnapshot: input.eligibility
      ? (input.eligibility.specSnapshot as unknown as Record<string, unknown>)
      : null,
  });

  await appendWpEvent(tx, {
    workspaceId: input.workspaceId,
    workPackageId: wp.workPackageId,
    eventType: "work_package.queued",
    actor: input.actor,
    after: { status: "QUEUED", effectivePriority: wp.effectivePriority },
    correlationId: input.correlationId,
  });
  await appendWpEvent(tx, {
    workspaceId: input.workspaceId,
    workPackageId: wp.workPackageId,
    eventType: "work_package.attempt_opened",
    actor: input.actor,
    after: { attemptId: attempt.attemptId, sequenceNo: 1 },
    correlationId: input.correlationId,
  });

  // Signed outbox dispatch → Agent Platform (Task 3). Chỉ opaque IDs.
  const correlationId = input.correlationId || generateSnowflake().toString();
  await appendOutboxEvent(
    tx,
    makeBusinessEvent({
      eventType: OPERATING_WORK_PACKAGE_QUEUED_V1,
      workspaceId: input.workspaceId,
      aggregateType: "work_package",
      aggregateId: wp.workPackageId,
      correlationId,
      actor: { kind: input.actor.kind as "user" | "agent" | "system", id: input.actor.id || "0" },
      classification: "internal",
      payload: {
        workspaceId: input.workspaceId,
        workPackageId: wp.workPackageId,
        workAttemptId: attempt.attemptId,
        agentInstanceId: input.assignedAgentInstanceId,
        assignmentId: input.eligibility?.assignmentId ?? "",
        effectivePriority: wp.effectivePriority,
        expectedCapabilityRefs: input.eligibility?.capabilityRefs ?? [],
        correlationId,
      },
    })
  );

  return { wp, attempt };
}

async function requireCurrentConfirmedContract(
  runner: Tx | typeof db,
  wsId: bigint,
  taskId: bigint,
  contractId: bigint
): Promise<void> {
  const [c] = await runner
    .select({
      id: taskOutcomeContracts.id,
      status: taskOutcomeContracts.status,
      taskId: taskOutcomeContracts.taskId,
    })
    .from(taskOutcomeContracts)
    .where(and(eq(taskOutcomeContracts.id, contractId), eq(taskOutcomeContracts.workspaceId, wsId)))
    .limit(1);
  if (!c || c.taskId !== taskId) {
    throw APIError.invalidArgument("outcomeContractId is not this task's contract in this workspace");
  }
  if (c.status !== "CONFIRMED") {
    throw APIError.failedPrecondition(`outcome contract is ${c.status}, not CONFIRMED`);
  }
}

/**
 * Tạo work package cho một task ĐÃ có CONFIRMED contract (queue gate). Package
 * mới ở QUEUED + attempt seq 1. Chưa bật live dispatch (Task 3).
 */
export async function createWorkPackage(
  input: {
    taskId: string;
    outcomeContractId: string;
    assignedAgentInstanceId: string;
    requestedPriority: Priority;
    objective: string;
    outputContract: Record<string, unknown>;
    acceptanceRubric: Record<string, number>;
    idempotencyKey: string;
    requestedByManagerId?: string;
  },
  ctx: TenantContext
): Promise<WorkPackageView> {
  const wsId = BigInt(ctx.workspaceId);
  validatePackageShape(input);

  if (input.idempotencyKey) {
    const hit = await idempotentHit(wsId, input.idempotencyKey);
    if (hit) return hit;
  }

  const [task] = await db
    .select({ id: tasks.id })
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(input.taskId)), eq(tasks.workspaceId, wsId)))
    .limit(1);
  if (!task) throw APIError.notFound(`task ${input.taskId} not found in workspace`);

  await assertTaskCanEnterQueue(input.taskId, ctx);
  await requireCurrentConfirmedContract(
    db,
    wsId,
    BigInt(input.taskId),
    BigInt(input.outcomeContractId)
  );

  const eligibility = await checkEligibility(ctx, input.assignedAgentInstanceId);

  const actor = { kind: ctx.userId ? "user" : "system", id: ctx.userId };
  const { wp } = await db.transaction((tx) =>
    insertQueuedPackage(tx, {
      workspaceId: ctx.workspaceId,
      taskId: input.taskId,
      outcomeContractId: input.outcomeContractId,
      assignedAgentInstanceId: input.assignedAgentInstanceId,
      requestedPriority: input.requestedPriority,
      objective: input.objective,
      outputContract: input.outputContract,
      acceptanceRubric: input.acceptanceRubric,
      idempotencyKey: input.idempotencyKey,
      requestedByManagerId: input.requestedByManagerId,
      actor,
      eligibility,
      correlationId: ctx.correlationId,
    })
  );
  return wp;
}

async function confirmContractInTx(
  tx: Tx,
  wsId: bigint,
  taskId: bigint,
  contractId: bigint,
  confirmedByMemberId: string | undefined
): Promise<void> {
  // Supersede mọi CONFIRMED cũ của task (an toàn kể cả khi chưa có).
  await tx
    .update(taskOutcomeContracts)
    .set({ status: "SUPERSEDED", updatedAt: new Date() })
    .where(
      and(
        eq(taskOutcomeContracts.taskId, taskId),
        eq(taskOutcomeContracts.workspaceId, wsId),
        eq(taskOutcomeContracts.status, "CONFIRMED")
      )
    );

  await tx
    .update(taskOutcomeContracts)
    .set({
      status: "CONFIRMED",
      confirmedAt: new Date(),
      confirmedByMemberId: confirmedByMemberId ? BigInt(confirmedByMemberId) : null,
      updatedAt: new Date(),
    })
    .where(and(eq(taskOutcomeContracts.id, contractId), eq(taskOutcomeContracts.workspaceId, wsId)));

  await tx
    .update(tasks)
    .set({ activeOutcomeContractId: contractId, status: "todo", updatedAt: new Date() })
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));
}

export interface AtomicQueueResult {
  task: { id: string; status: string };
  contract: { id: string; status: string; revision: number };
  workPackage: WorkPackageView;
}

/**
 * Lệnh public manager/founder: một transaction tạo task bình thường + CONFIRMED
 * contract + initial work package QUEUED + attempt seq 1 + events. Không bao giờ
 * để lại task đã xác nhận ở TODO/DRAFT (spec §6.1).
 */
export async function createConfirmedTaskAndQueue(
  input: {
    task: { title: string; initiativeId?: string; priority: "low" | "medium" | "high" | "urgent" };
    contract: Omit<CreateTaskOutcomeContractInput, "workspaceId" | "taskId">;
    initialPackage: {
      assignedAgentInstanceId: string;
      objective: string;
      outputContract: Record<string, unknown>;
      acceptanceRubric: Record<string, number>;
      requestedPriority?: Priority;
    };
    idempotencyKey: string;
  },
  ctx: TenantContext
): Promise<AtomicQueueResult> {
  const wsId = BigInt(ctx.workspaceId);
  const priority: Priority = input.initialPackage.requestedPriority ?? "P1";
  validatePackageShape({ ...input.initialPackage, requestedPriority: priority });

  const hit = await idempotentHit(wsId, input.idempotencyKey);
  if (hit) {
    return {
      task: { id: hit.taskId, status: "todo" },
      contract: { id: hit.outcomeContractId, status: "CONFIRMED", revision: 1 },
      workPackage: hit,
    };
  }

  const eligibility = await checkEligibility(ctx, input.initialPackage.assignedAgentInstanceId);
  const actor = { kind: ctx.userId ? "user" : "system", id: ctx.userId };
  return db.transaction(async (tx) => {
    const [taskRow] = await tx
      .insert(tasks)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        title: input.task.title,
        status: "todo",
        priority: input.task.priority,
        source: "manager_create",
        initiativeId: input.task.initiativeId ? BigInt(input.task.initiativeId) : null,
      })
      .returning();
    if (!taskRow) throw APIError.internal("failed to create task");

    const contract = await insertContractRevision(
      tx,
      {
        ...input.contract,
        workspaceId: ctx.workspaceId,
        taskId: taskRow.id.toString(),
        initiativeId: input.contract.initiativeId ?? input.task.initiativeId,
      },
      { status: "CONFIRMED", revision: 1, confirmedByMemberId: ctx.workforceMemberId }
    );

    await confirmContractInTx(
      tx,
      wsId,
      taskRow.id,
      BigInt(contract.id),
      ctx.workforceMemberId
    );

    const { wp } = await insertQueuedPackage(tx, {
      workspaceId: ctx.workspaceId,
      taskId: taskRow.id.toString(),
      outcomeContractId: contract.id,
      assignedAgentInstanceId: input.initialPackage.assignedAgentInstanceId,
      requestedPriority: priority,
      objective: input.initialPackage.objective,
      outputContract: input.initialPackage.outputContract,
      acceptanceRubric: input.initialPackage.acceptanceRubric,
      idempotencyKey: input.idempotencyKey,
      requestedByManagerId: ctx.workforceMemberId,
      actor,
      eligibility,
      correlationId: ctx.correlationId,
    });

    return {
      task: { id: taskRow.id.toString(), status: "todo" },
      contract: { id: contract.id, status: "CONFIRMED", revision: contract.revision },
      workPackage: wp,
    };
  });
}

/**
 * Manager/founder xác nhận một AI proposal: áp patch thành một revision
 * CONFIRMED mới (append), materialize task, tạo initial work package QUEUED.
 * Không bao giờ để proposal đã xác nhận ở DRAFT/TODO.
 */
export async function confirmAiProposalAndQueue(
  input: {
    proposalTaskId: string;
    draftContractId: string;
    contractPatch: Partial<CreateTaskOutcomeContractInput>;
    initialPackage: {
      assignedAgentInstanceId: string;
      objective: string;
      outputContract: Record<string, unknown>;
      acceptanceRubric: Record<string, number>;
      requestedPriority?: Priority;
    };
    expectedVersion: number;
    idempotencyKey: string;
  },
  ctx: TenantContext
): Promise<AtomicQueueResult> {
  const wsId = BigInt(ctx.workspaceId);
  const priority: Priority = input.initialPackage.requestedPriority ?? "P1";
  validatePackageShape({ ...input.initialPackage, requestedPriority: priority });

  const hit = await idempotentHit(wsId, input.idempotencyKey);
  if (hit) {
    return {
      task: { id: hit.taskId, status: "todo" },
      contract: { id: hit.outcomeContractId, status: "CONFIRMED", revision: 0 },
      workPackage: hit,
    };
  }

  const [draft] = await db
    .select()
    .from(taskOutcomeContracts)
    .where(
      and(
        eq(taskOutcomeContracts.id, BigInt(input.draftContractId)),
        eq(taskOutcomeContracts.workspaceId, wsId),
        eq(taskOutcomeContracts.taskId, BigInt(input.proposalTaskId))
      )
    )
    .limit(1);
  if (!draft) throw APIError.notFound("draft contract not found for proposal task in workspace");
  if (draft.status !== "DRAFT") {
    throw APIError.failedPrecondition(`contract is ${draft.status}, not DRAFT`);
  }
  if (draft.version !== input.expectedVersion) {
    throw APIError.aborted(
      `stale contract version: expected ${input.expectedVersion}, got ${draft.version}`
    );
  }

  const eligibility = await checkEligibility(ctx, input.initialPackage.assignedAgentInstanceId);
  const actor = { kind: ctx.userId ? "user" : "system", id: ctx.userId };
  return db.transaction(async (tx) => {
    // Áp patch của manager thành một confirmed revision mới (append).
    const merged: CreateTaskOutcomeContractInput = {
      workspaceId: ctx.workspaceId,
      taskId: input.proposalTaskId,
      outcomeType: (input.contractPatch.outcomeType ?? draft.outcomeType) as CreateTaskOutcomeContractInput["outcomeType"],
      expectedOutcome: input.contractPatch.expectedOutcome ?? draft.expectedOutcome,
      acceptanceCriteria:
        input.contractPatch.acceptanceCriteria ??
        ((draft.acceptanceCriteria ?? {}) as Record<string, unknown>),
      expectedEvidenceRefs:
        input.contractPatch.expectedEvidenceRefs ??
        (Array.isArray(draft.expectedEvidenceRefs) ? (draft.expectedEvidenceRefs as string[]) : []),
      impactHypothesis: input.contractPatch.impactHypothesis ?? draft.impactHypothesis,
      measurementPlan:
        input.contractPatch.measurementPlan ??
        ((draft.measurementPlan ?? undefined) as Record<string, unknown> | undefined),
      primaryKrId:
        input.contractPatch.primaryKrId ??
        (draft.primaryKrId ? draft.primaryKrId.toString() : undefined),
      serviceObjective: input.contractPatch.serviceObjective ?? draft.serviceObjective ?? undefined,
      initiativeId:
        input.contractPatch.initiativeId ??
        (draft.initiativeId ? draft.initiativeId.toString() : undefined),
      secondaryKrLinks: input.contractPatch.secondaryKrLinks,
    };

    const confirmedRev = await insertContractRevision(tx, merged, {
      status: "CONFIRMED",
      revision: draft.revision + 1,
      supersedesContractId: input.draftContractId,
      changeReason: "manager confirmation",
      confirmedByMemberId: ctx.workforceMemberId,
    });

    await tx
      .update(taskOutcomeContracts)
      .set({ status: "SUPERSEDED", updatedAt: new Date() })
      .where(
        and(
          eq(taskOutcomeContracts.id, BigInt(input.draftContractId)),
          eq(taskOutcomeContracts.workspaceId, wsId)
        )
      );

    await confirmContractInTx(tx, wsId, BigInt(input.proposalTaskId), BigInt(confirmedRev.id), ctx.workforceMemberId);

    const { wp } = await insertQueuedPackage(tx, {
      workspaceId: ctx.workspaceId,
      taskId: input.proposalTaskId,
      outcomeContractId: confirmedRev.id,
      assignedAgentInstanceId: input.initialPackage.assignedAgentInstanceId,
      requestedPriority: priority,
      objective: input.initialPackage.objective,
      outputContract: input.initialPackage.outputContract,
      acceptanceRubric: input.initialPackage.acceptanceRubric,
      idempotencyKey: input.idempotencyKey,
      requestedByManagerId: ctx.workforceMemberId,
      actor,
      eligibility,
      correlationId: ctx.correlationId,
    });

    return {
      task: { id: input.proposalTaskId, status: "todo" },
      contract: { id: confirmedRev.id, status: "CONFIRMED", revision: confirmedRev.revision },
      workPackage: wp,
    };
  });
}

/**
 * Reassign: đổi employee cho package. Nếu chưa lease/chạy: đóng attempt cũ
 * (unleased), mở attempt kế tiếp, ghi attribution cũ/mới, bump version. Nếu
 * đang LEASED/RUNNING: chỉ ghi reassignment_requested (áp dụng tại checkpoint,
 * Task 4).
 */
export async function reassignWorkPackage(
  input: {
    workPackageId: string;
    targetAgentInstanceId: string;
    expectedVersion: number;
    reason?: string;
  },
  ctx: TenantContext
): Promise<WorkPackageView> {
  const wsId = BigInt(ctx.workspaceId);
  const actor = { kind: ctx.userId ? "user" : "system", id: ctx.userId };

  // Fail-closed eligibility cho employee đích TRƯỚC khi mở transaction (không
  // ghi attempt nếu Control Plane từ chối).
  const eligibility = await checkEligibility(ctx, input.targetAgentInstanceId);

  return db.transaction(async (tx) => {
    const [wp] = await tx
      .select()
      .from(taskWorkPackages)
      .where(
        and(
          eq(taskWorkPackages.id, BigInt(input.workPackageId)),
          eq(taskWorkPackages.workspaceId, wsId)
        )
      )
      .limit(1);
    if (!wp) throw APIError.notFound("work package not found in workspace");
    if (wp.version !== input.expectedVersion) {
      throw APIError.aborted(
        `stale work package version: expected ${input.expectedVersion}, got ${wp.version}`
      );
    }

    const oldAssignee = wp.assignedAgentInstanceId;
    const correlationId = ctx.correlationId || generateSnowflake().toString();

    if (LEASED_WP_STATUSES.includes(wp.status as WorkPackageStatus)) {
      await appendWpEvent(tx, {
        workspaceId: ctx.workspaceId,
        workPackageId: input.workPackageId,
        eventType: "work_package.reassignment_requested",
        actor,
        before: { assignedAgentInstanceId: oldAssignee },
        after: { targetAgentInstanceId: input.targetAgentInstanceId },
        reason: input.reason,
        correlationId,
      });
      await appendOutboxEvent(
        tx,
        makeBusinessEvent({
          eventType: OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1,
          workspaceId: ctx.workspaceId,
          aggregateType: "work_package",
          aggregateId: input.workPackageId,
          correlationId,
          actor: { kind: actor.kind as "user" | "agent" | "system", id: actor.id || "0" },
          classification: "internal",
          payload: {
            workspaceId: ctx.workspaceId,
            workPackageId: input.workPackageId,
            fromAgentInstanceId: oldAssignee,
            targetAgentInstanceId: input.targetAgentInstanceId,
            correlationId,
          },
        })
      );
      return toWpView(wp);
    }

    const [activeAttempt] = await tx
      .select()
      .from(workPackageAttempts)
      .where(
        and(
          eq(workPackageAttempts.workPackageId, wp.id),
          isNull(workPackageAttempts.endedAt)
        )
      )
      .limit(1);
    if (activeAttempt) {
      await tx
        .update(workPackageAttempts)
        .set({ endedAt: new Date(), status: "REASSIGNED", endedReason: input.reason ?? "reassigned" })
        .where(eq(workPackageAttempts.id, activeAttempt.id));
    }

    const nextAttempt = await openAttempt(tx, {
      workspaceId: ctx.workspaceId,
      workPackageId: input.workPackageId,
      assignedAgentInstanceId: input.targetAgentInstanceId,
      assignmentSnapshot: eligibility ? { assignmentId: eligibility.assignmentId } : null,
      specSnapshot: eligibility
        ? (eligibility.specSnapshot as unknown as Record<string, unknown>)
        : null,
    });

    const [updated] = await tx
      .update(taskWorkPackages)
      .set({
        assignedAgentInstanceId: input.targetAgentInstanceId,
        status: "QUEUED",
        version: wp.version + 1,
        updatedAt: new Date(),
      })
      .where(and(eq(taskWorkPackages.id, wp.id), eq(taskWorkPackages.version, wp.version)))
      .returning();
    if (!updated) throw APIError.aborted("work package changed concurrently");

    await appendWpEvent(tx, {
      workspaceId: ctx.workspaceId,
      workPackageId: input.workPackageId,
      eventType: "work_package.reassigned",
      actor,
      before: { assignedAgentInstanceId: oldAssignee, closedAttemptId: activeAttempt?.id.toString() },
      after: {
        assignedAgentInstanceId: input.targetAgentInstanceId,
        newAttemptId: nextAttempt.attemptId,
      },
      reason: input.reason,
    });

    return toWpView(updated);
  });
}

export async function listAttempts(
  workPackageId: string,
  ctx?: TenantContext
): Promise<AttemptView[]> {
  const conds = [eq(workPackageAttempts.workPackageId, BigInt(workPackageId))];
  if (ctx) conds.push(eq(workPackageAttempts.workspaceId, BigInt(ctx.workspaceId)));
  const rows = await db
    .select()
    .from(workPackageAttempts)
    .where(and(...conds))
    .orderBy(asc(workPackageAttempts.sequenceNo));
  return rows.map(toAttemptView);
}

export async function listWorkPackagesForTask(
  taskId: string,
  ctx?: TenantContext
): Promise<WorkPackageView[]> {
  const conds = [eq(taskWorkPackages.taskId, BigInt(taskId))];
  if (ctx) conds.push(eq(taskWorkPackages.workspaceId, BigInt(ctx.workspaceId)));
  const rows = await db
    .select()
    .from(taskWorkPackages)
    .where(and(...conds))
    .orderBy(asc(taskWorkPackages.createdAt));
  return rows.map(toWpView);
}

export async function getWorkPackage(
  workPackageId: string,
  ctx: TenantContext
): Promise<WorkPackageView> {
  const [row] = await db
    .select()
    .from(taskWorkPackages)
    .where(
      and(
        eq(taskWorkPackages.id, BigInt(workPackageId)),
        eq(taskWorkPackages.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);
  if (!row) throw APIError.notFound("work package not found in workspace");
  return toWpView(row);
}
