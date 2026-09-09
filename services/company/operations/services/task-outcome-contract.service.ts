import { APIError } from "encore.dev/api";
import { and, eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { initiatives, initiativeKeyResults, keyResults } from "../../shared/db/schema/operations";

const { taskOutcomeContracts, taskOutcomeKrLinks, tasks } = schema;

// Transaction type dùng chung cho các slice atomically tạo task + contract
// (Task 2). Task 1A chỉ mở đường AI proposal + queue gate.
export type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

export type TaskOutcomeType = "DIRECT_KR" | "ENABLING_KR" | "VALIDATION" | "BAU";
export type TaskOutcomeContractStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";
export type KrRelationType = "DIRECT" | "ENABLING" | "VALIDATION";

const OUTCOME_TYPES: readonly TaskOutcomeType[] = [
  "DIRECT_KR",
  "ENABLING_KR",
  "VALIDATION",
  "BAU",
];
const KR_RELATION_TYPES: readonly KrRelationType[] = ["DIRECT", "ENABLING", "VALIDATION"];

export interface SecondaryKrLink {
  keyResultId: string;
  relationType: KrRelationType;
}

export interface CreateTaskOutcomeContractInput {
  workspaceId: string;
  taskId: string;
  outcomeType: TaskOutcomeType;
  expectedOutcome: string;
  acceptanceCriteria: Record<string, unknown>;
  expectedEvidenceRefs: string[];
  impactHypothesis: string;
  measurementPlan?: Record<string, unknown>;
  primaryKrId?: string;
  secondaryKrLinks?: SecondaryKrLink[];
  serviceObjective?: string;
  initiativeId?: string;
}

export interface TaskOutcomeContractView {
  id: string;
  workspaceId: string;
  taskId: string;
  revision: number;
  status: TaskOutcomeContractStatus;
  outcomeType: TaskOutcomeType;
  expectedOutcome: string;
  acceptanceCriteria: Record<string, unknown>;
  expectedEvidenceRefs: string[];
  measurementPlan: Record<string, unknown> | null;
  impactHypothesis: string;
  serviceObjective: string | null;
  primaryKrId: string | null;
  initiativeId: string | null;
  secondaryKrLinks: SecondaryKrLink[];
  proposedByAgentInstanceId: string | null;
  supersedesContractId: string | null;
  confirmedAt: string | null;
  version: number;
  createdAt: string;
}

export interface ValidatedTaskOutcomeContract {
  contractId: string;
  taskId: string;
  workspaceId: string;
  revision: number;
  status: TaskOutcomeContractStatus;
  outcomeType: TaskOutcomeType;
  initiativeId: string | null;
  primaryKrId: string | null;
  serviceObjective: string | null;
  acceptanceCriteria: Record<string, unknown>;
  expectedEvidenceRefs: string[];
  krLinks: SecondaryKrLink[];
}

function toView(
  row: typeof taskOutcomeContracts.$inferSelect,
  krLinks: SecondaryKrLink[]
): TaskOutcomeContractView {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    taskId: row.taskId.toString(),
    revision: row.revision,
    status: row.status as TaskOutcomeContractStatus,
    outcomeType: row.outcomeType as TaskOutcomeType,
    expectedOutcome: row.expectedOutcome,
    acceptanceCriteria: (row.acceptanceCriteria ?? {}) as Record<string, unknown>,
    expectedEvidenceRefs: Array.isArray(row.expectedEvidenceRefs)
      ? (row.expectedEvidenceRefs as string[])
      : [],
    measurementPlan: (row.measurementPlan ?? null) as Record<string, unknown> | null,
    impactHypothesis: row.impactHypothesis,
    serviceObjective: row.serviceObjective ?? null,
    primaryKrId: row.primaryKrId ? row.primaryKrId.toString() : null,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    secondaryKrLinks: krLinks,
    proposedByAgentInstanceId: row.proposedByAgentInstanceId ?? null,
    supersedesContractId: row.supersedesContractId ? row.supersedesContractId.toString() : null,
    confirmedAt: row.confirmedAt ? row.confirmedAt.toISOString() : null,
    version: row.version,
    createdAt: row.createdAt.toISOString(),
  };
}

/**
 * Kiểm tra tính hợp lệ nghiệp vụ của một Outcome Contract input trước khi ghi.
 * Non-BAU: bắt buộc một primary KR, một Initiative APPROVED và mọi KR (chính +
 * phụ) phải thuộc workspace và được link vào Initiative đó. BAU: bắt buộc
 * `serviceObjective`, không nhận primary KR. Không side-effect.
 */
export async function validateContractInput(
  input: CreateTaskOutcomeContractInput,
  runner: Tx | typeof db = db,
  opts: { strict?: boolean } = {}
): Promise<{ initiativeId: bigint | null; primaryKrId: bigint | null; secondary: SecondaryKrLink[] }> {
  // strict = true khi contract sắp CONFIRMED (Task 2). strict = false cho AI
  // proposal DRAFT: input có thể còn thiếu KR/Initiative (spec §6.1 "input
  // không đủ chuẩn"), nhưng BAU vẫn phải có service objective và mọi ID đã
  // cung cấp vẫn phải hợp lệ + tenant-scoped.
  const strict = opts.strict ?? false;

  if (!OUTCOME_TYPES.includes(input.outcomeType)) {
    throw APIError.invalidArgument(`outcomeType must be one of ${OUTCOME_TYPES.join(", ")}`);
  }
  if (!input.expectedOutcome?.trim()) {
    throw APIError.invalidArgument("expectedOutcome is required");
  }
  if (!input.impactHypothesis?.trim()) {
    throw APIError.invalidArgument("impactHypothesis is required");
  }

  const wsId = BigInt(input.workspaceId);
  const secondary = (input.secondaryKrLinks ?? []).map((l) => {
    if (!KR_RELATION_TYPES.includes(l.relationType)) {
      throw APIError.invalidArgument(
        `secondary KR relationType must be one of ${KR_RELATION_TYPES.join(", ")}`
      );
    }
    return l;
  });

  const isBau = input.outcomeType === "BAU";
  if (isBau) {
    if (!input.serviceObjective?.trim()) {
      throw APIError.invalidArgument("BAU tasks require a service objective / SLO");
    }
    if (input.primaryKrId) {
      throw APIError.invalidArgument("BAU tasks must not link a primary KR; use a service objective");
    }
  } else if (strict) {
    if (!input.primaryKrId) {
      throw APIError.invalidArgument("non-BAU tasks require exactly one primary KR");
    }
    if (!input.initiativeId) {
      throw APIError.invalidArgument("non-BAU tasks require an APPROVED Initiative");
    }
  }

  let initiativeId: bigint | null = null;
  if (input.initiativeId) {
    const [init] = await runner
      .select({ id: initiatives.id, approvalStatus: initiatives.approvalStatus })
      .from(initiatives)
      .where(and(eq(initiatives.id, BigInt(input.initiativeId)), eq(initiatives.workspaceId, wsId)))
      .limit(1);
    if (!init) {
      throw APIError.notFound(`Initiative ${input.initiativeId} not found in workspace`);
    }
    if (strict && !isBau && init.approvalStatus !== "APPROVED") {
      throw APIError.invalidArgument(
        `Initiative ${input.initiativeId} must be APPROVED (current: ${init.approvalStatus})`
      );
    }
    initiativeId = init.id;
  }

  // Tất cả KR id được tham chiếu phải thuộc workspace.
  const allKrIds = [
    ...(input.primaryKrId ? [input.primaryKrId] : []),
    ...secondary.map((l) => l.keyResultId),
  ].map((s) => BigInt(s));
  if (allKrIds.length > 0) {
    const rows = await runner
      .select({ id: keyResults.id })
      .from(keyResults)
      .where(and(inArray(keyResults.id, allKrIds), eq(keyResults.workspaceId, wsId)));
    const found = new Set(rows.map((r) => r.id.toString()));
    for (const krId of allKrIds) {
      if (!found.has(krId.toString())) {
        throw APIError.notFound(`Key Result ${krId} not found in workspace`);
      }
    }

    // KR phải được link vào Initiative (nếu có Initiative).
    if (initiativeId !== null) {
      const linkRows = await runner
        .select({ keyResultId: initiativeKeyResults.keyResultId })
        .from(initiativeKeyResults)
        .where(
          and(
            eq(initiativeKeyResults.workspaceId, wsId),
            eq(initiativeKeyResults.initiativeId, initiativeId),
            inArray(initiativeKeyResults.keyResultId, allKrIds)
          )
        );
      const linked = new Set(linkRows.map((r) => r.keyResultId.toString()));
      for (const krId of allKrIds) {
        if (!linked.has(krId.toString())) {
          throw APIError.invalidArgument(
            `Key Result ${krId} is not linked to Initiative ${initiativeId}`
          );
        }
      }
    }
  }

  return {
    initiativeId,
    primaryKrId: input.primaryKrId ? BigInt(input.primaryKrId) : null,
    secondary,
  };
}

/**
 * Ghi một contract revision mới (APPEND-only) + KR links, trong transaction
 * cho trước. Dùng bởi AI proposal path (Task 1A, status DRAFT) và bởi
 * manager/founder confirmation atomically (Task 2, status CONFIRMED).
 */
export async function insertContractRevision(
  tx: Tx,
  input: CreateTaskOutcomeContractInput,
  opts: {
    status: TaskOutcomeContractStatus;
    revision: number;
    proposedByAgentInstanceId?: string;
    createdByMemberId?: string;
    confirmedByMemberId?: string;
    supersedesContractId?: string;
    changeReason?: string;
  }
): Promise<TaskOutcomeContractView> {
  const validated = await validateContractInput(input, tx, {
    strict: opts.status === "CONFIRMED",
  });
  const now = new Date();
  const [row] = await tx
    .insert(taskOutcomeContracts)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(input.workspaceId),
      taskId: BigInt(input.taskId),
      revision: opts.revision,
      status: opts.status,
      outcomeType: input.outcomeType,
      expectedOutcome: input.expectedOutcome,
      acceptanceCriteria: input.acceptanceCriteria ?? {},
      expectedEvidenceRefs: input.expectedEvidenceRefs ?? [],
      measurementPlan: input.measurementPlan ?? null,
      impactHypothesis: input.impactHypothesis,
      serviceObjective: input.serviceObjective ?? null,
      primaryKrId: validated.primaryKrId,
      initiativeId: validated.initiativeId,
      proposedByAgentInstanceId: opts.proposedByAgentInstanceId ?? null,
      createdByMemberId: opts.createdByMemberId ? BigInt(opts.createdByMemberId) : null,
      confirmedByMemberId: opts.confirmedByMemberId ? BigInt(opts.confirmedByMemberId) : null,
      confirmedAt: opts.status === "CONFIRMED" ? now : null,
      supersedesContractId: opts.supersedesContractId ? BigInt(opts.supersedesContractId) : null,
      changeReason: opts.changeReason ?? null,
    })
    .returning();
  if (!row) throw APIError.internal("failed to create outcome contract");

  const krLinks: SecondaryKrLink[] = [];
  if (validated.primaryKrId !== null) {
    await tx.insert(taskOutcomeKrLinks).values({
      id: generateSnowflake(),
      workspaceId: BigInt(input.workspaceId),
      contractId: row.id,
      keyResultId: validated.primaryKrId,
      relationType: input.outcomeType === "ENABLING_KR" ? "ENABLING" : "DIRECT",
      isPrimary: true,
    });
  }
  for (const link of validated.secondary) {
    await tx.insert(taskOutcomeKrLinks).values({
      id: generateSnowflake(),
      workspaceId: BigInt(input.workspaceId),
      contractId: row.id,
      keyResultId: BigInt(link.keyResultId),
      relationType: link.relationType,
      isPrimary: false,
    });
    krLinks.push(link);
  }

  return toView(row, krLinks);
}

/**
 * Đường nội bộ DUY NHẤT cho AI đề xuất một Outcome Contract. Luôn tạo revision
 * 1 với status DRAFT. KHÔNG tạo queue entry / work package (spec §6.1). Task
 * proposal phải đã tồn tại (do đường AI proposal của task.service tạo).
 */
export async function createTaskOutcomeProposal(
  input: CreateTaskOutcomeContractInput & { proposedByAgentInstanceId: string },
  ctx: TenantContext
): Promise<TaskOutcomeContractView> {
  if (input.workspaceId !== ctx.workspaceId) {
    throw APIError.permissionDenied("workspace mismatch");
  }
  const wsId = BigInt(ctx.workspaceId);
  const [task] = await db
    .select({ id: tasks.id })
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(input.taskId)), eq(tasks.workspaceId, wsId)))
    .limit(1);
  if (!task) throw APIError.notFound(`task ${input.taskId} not found in workspace`);

  const [existing] = await db
    .select({ id: taskOutcomeContracts.id })
    .from(taskOutcomeContracts)
    .where(
      and(
        eq(taskOutcomeContracts.taskId, BigInt(input.taskId)),
        eq(taskOutcomeContracts.workspaceId, wsId)
      )
    )
    .limit(1);
  if (existing) {
    throw APIError.alreadyExists(`task ${input.taskId} already has an outcome contract`);
  }

  return db.transaction((tx) =>
    insertContractRevision(tx, { ...input, workspaceId: ctx.workspaceId }, {
      status: "DRAFT",
      revision: 1,
      proposedByAgentInstanceId: input.proposedByAgentInstanceId,
    })
  );
}

async function loadContractWithLinks(
  contractId: string,
  wsId: bigint
): Promise<{ row: typeof taskOutcomeContracts.$inferSelect; links: SecondaryKrLink[] }> {
  const [row] = await db
    .select()
    .from(taskOutcomeContracts)
    .where(
      and(
        eq(taskOutcomeContracts.id, BigInt(contractId)),
        eq(taskOutcomeContracts.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!row) throw APIError.notFound(`Outcome Contract ${contractId} not found in workspace`);

  const linkRows = await db
    .select()
    .from(taskOutcomeKrLinks)
    .where(eq(taskOutcomeKrLinks.contractId, row.id));
  const links: SecondaryKrLink[] = linkRows
    .filter((l) => !l.isPrimary)
    .map((l) => ({
      keyResultId: l.keyResultId.toString(),
      relationType: l.relationType as KrRelationType,
    }));
  return { row, links };
}

/**
 * Trả về các "facts" bất biến của một contract để manager review trước khi
 * queue. KHÔNG đổi status. Public manager/founder confirmation (đổi DRAFT →
 * CONFIRMED) chỉ mở ở Task 2 khi có thể tạo initial work package atomically.
 */
export async function validateTaskOutcomeContractForQueue(
  contractId: string,
  ctx: TenantContext
): Promise<ValidatedTaskOutcomeContract> {
  const wsId = BigInt(ctx.workspaceId);
  const { row, links } = await loadContractWithLinks(contractId, wsId);
  return {
    contractId: row.id.toString(),
    taskId: row.taskId.toString(),
    workspaceId: row.workspaceId.toString(),
    revision: row.revision,
    status: row.status as TaskOutcomeContractStatus,
    outcomeType: row.outcomeType as TaskOutcomeType,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    primaryKrId: row.primaryKrId ? row.primaryKrId.toString() : null,
    serviceObjective: row.serviceObjective ?? null,
    acceptanceCriteria: (row.acceptanceCriteria ?? {}) as Record<string, unknown>,
    expectedEvidenceRefs: Array.isArray(row.expectedEvidenceRefs)
      ? (row.expectedEvidenceRefs as string[])
      : [],
    krLinks: links,
  };
}

export async function getTaskOutcomeContract(
  contractId: string,
  ctx: TenantContext
): Promise<TaskOutcomeContractView> {
  const wsId = BigInt(ctx.workspaceId);
  const { row, links } = await loadContractWithLinks(contractId, wsId);
  return toView(row, links);
}

/**
 * Queue gate (spec §6.1). Từ chối khi task chưa có Outcome Contract, contract
 * còn DRAFT/SUPERSEDED, hoặc contract thuộc workspace khác. Task 2 bổ sung
 * điều kiện "confirmed task phải có initial work package".
 */
export async function assertTaskCanEnterQueue(
  taskId: string,
  ctx: TenantContext,
  runner: Tx | typeof db = db
): Promise<{ contractId: string; contractRevision: number }> {
  const wsId = BigInt(ctx.workspaceId);
  const [task] = await runner
    .select({ id: tasks.id, activeOutcomeContractId: tasks.activeOutcomeContractId })
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(taskId)), eq(tasks.workspaceId, wsId)))
    .limit(1);
  if (!task) throw APIError.notFound(`task ${taskId} not found in workspace`);

  if (!task.activeOutcomeContractId) {
    throw APIError.failedPrecondition(
      `task ${taskId} has no confirmed Outcome Contract and cannot enter the queue`
    );
  }

  const [contract] = await runner
    .select({
      id: taskOutcomeContracts.id,
      status: taskOutcomeContracts.status,
      revision: taskOutcomeContracts.revision,
      taskId: taskOutcomeContracts.taskId,
    })
    .from(taskOutcomeContracts)
    .where(
      and(
        eq(taskOutcomeContracts.id, task.activeOutcomeContractId),
        eq(taskOutcomeContracts.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!contract || contract.taskId.toString() !== taskId) {
    throw APIError.failedPrecondition(
      `task ${taskId} references a foreign or missing Outcome Contract`
    );
  }
  if (contract.status !== "CONFIRMED") {
    throw APIError.failedPrecondition(
      `Outcome Contract for task ${taskId} is ${contract.status}, not CONFIRMED`
    );
  }
  return { contractId: contract.id.toString(), contractRevision: contract.revision };
}
