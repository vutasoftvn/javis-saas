import { APIError } from "encore.dev/api";
import { and, eq, gt, desc, isNull, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mvpList, mvpItem, MvpSuccess, MvpSourceRef } from "../../shared/contracts/mvp-response";

const { tasks, taskDependencies, runtimeSourceSignals, runtimeSnoozes } = schema;

export interface RuntimeItem {
  id: string;
  workspaceId: string;
  sourceKind: string;
  sourceId: string;
  title: string;
  description: string | null;
  state: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  sourceRef: MvpSourceRef;
  actionUrl: string | null;
  createdAt: string;
  observedAt: string;
}

export interface RuntimeItemDetail extends RuntimeItem {
  payload: Record<string, unknown>;
  dependencies: readonly string[];
}

export interface SourceStatus {
  sourceKind: string;
  plane: string;
  status: "HEALTHY" | "DEGRADED" | "UNAVAILABLE";
  lastObservedAt: string;
}

export async function getNeedsYouService(ctx: TenantContext): Promise<MvpSuccess<readonly RuntimeItem[]>> {
  const wsId = BigInt(ctx.workspaceId);
  const now = new Date();

  // Find active snoozes for current actor
  const activeSnoozes = ctx.memberId
    ? await db
        .select()
        .from(runtimeSnoozes)
        .where(
          and(
            eq(runtimeSnoozes.workspaceId, wsId),
            eq(runtimeSnoozes.actorMemberId, BigInt(ctx.memberId)),
            gt(runtimeSnoozes.snoozedUntil, now)
          )
        )
    : [];

  const snoozedKeys = new Set(activeSnoozes.map((s) => `${s.sourceKind}:${s.sourceId}`));

  const items: RuntimeItem[] = [];

  // 1. Pending tasks assigned to actor (or unassigned needing attention)
  if (ctx.memberId) {
    const memberTasks = await db
      .select()
      .from(tasks)
      .where(
        and(
          eq(tasks.workspaceId, wsId),
          eq(tasks.assigneeMemberId, BigInt(ctx.memberId)),
          isNull(tasks.deletedAt),
          inArray(tasks.status, ["TODO", "IN_PROGRESS", "REVIEW"])
        )
      )
      .limit(20);

    for (const t of memberTasks) {
      const key = `task:${t.id}`;
      if (snoozedKeys.has(key)) continue;
      items.push({
        id: `need_${t.id}`,
        workspaceId: ctx.workspaceId.toString(),
        sourceKind: "company_db",
        sourceId: t.id.toString(),
        title: t.title,
        description: t.description,
        state: t.status,
        severity: t.priority === "URGENT" || t.priority === "HIGH" ? "HIGH" : "MEDIUM",
        sourceRef: { kind: "company_db", ref: `operating.tasks:${t.id}` },
        actionUrl: `/operations/tasks/${t.id}`,
        createdAt: t.createdAt.toISOString(),
        observedAt: t.updatedAt.toISOString(),
      });
    }
  }

  // 2. Projected agent signals needing user attention (e.g. APPROVAL_REQUIRED, PAUSED)
  const agentSignals = await db
    .select()
    .from(runtimeSourceSignals)
    .where(
      and(
        eq(runtimeSourceSignals.workspaceId, wsId),
        inArray(runtimeSourceSignals.state, ["APPROVAL_REQUIRED", "NEEDS_INPUT", "PAUSED"])
      )
    )
    .orderBy(desc(runtimeSourceSignals.observedAt))
    .limit(20);

  for (const sig of agentSignals) {
    const key = `${sig.sourceKind}:${sig.sourceId}`;
    if (snoozedKeys.has(key)) continue;
    items.push({
      id: `sig_${sig.id}`,
      workspaceId: ctx.workspaceId.toString(),
      sourceKind: sig.sourceKind,
      sourceId: sig.sourceId,
      title: `Agent Action Required: ${sig.sourceKind} (${sig.state})`,
      description: `State: ${sig.state}, correlationId: ${sig.correlationId}`,
      state: sig.state,
      severity: "HIGH",
      sourceRef: { kind: "agent_db", ref: `agent.${sig.sourceKind}:${sig.sourceId}` },
      actionUrl: `/agent/workforce/${sig.sourceKind}/${sig.sourceId}`,
      createdAt: sig.receivedAt.toISOString(),
      observedAt: sig.observedAt.toISOString(),
    });
  }

  return mvpList(items, [
    { kind: "company_db", ref: "operating.tasks" },
    { kind: "agent_db", ref: "operating.runtime_source_signals" },
  ]);
}

export async function getBlockersService(ctx: TenantContext): Promise<MvpSuccess<readonly RuntimeItem[]>> {
  const wsId = BigInt(ctx.workspaceId);

  const blockers: RuntimeItem[] = [];

  // 1. Unresolved task dependencies
  const deps = await db
    .select({
      id: taskDependencies.id,
      taskId: taskDependencies.taskId,
      blockingTaskId: taskDependencies.dependsOnTaskId,
      createdAt: taskDependencies.createdAt,
      taskTitle: tasks.title,
      taskStatus: tasks.status,
    })
    .from(taskDependencies)
    .innerJoin(tasks, eq(taskDependencies.taskId, tasks.id))
    .where(and(eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)))
    .limit(20);

  for (const d of deps) {
    if (d.taskStatus !== "DONE" && d.taskStatus !== "COMPLETED") {
      blockers.push({
        id: `dep_${d.id}`,
        workspaceId: ctx.workspaceId.toString(),
        sourceKind: "company_db",
        sourceId: d.taskId.toString(),
        title: `Blocked Task: ${d.taskTitle}`,
        description: `Waiting on dependency task #${d.blockingTaskId}`,
        state: "BLOCKED",
        severity: "HIGH",
        sourceRef: { kind: "company_db", ref: `operating.task_dependencies:${d.id}` },
        actionUrl: `/operations/tasks/${d.taskId}`,
        createdAt: d.createdAt.toISOString(),
        observedAt: d.createdAt.toISOString(),
      });
    }
  }

  // 2. Projected agent failure signals
  const failedSignals = await db
    .select()
    .from(runtimeSourceSignals)
    .where(
      and(
        eq(runtimeSourceSignals.workspaceId, wsId),
        inArray(runtimeSourceSignals.state, ["FAILED", "ERROR", "CRASHED"])
      )
    )
    .orderBy(desc(runtimeSourceSignals.observedAt))
    .limit(20);

  for (const sig of failedSignals) {
    blockers.push({
      id: `sig_${sig.id}`,
      workspaceId: ctx.workspaceId.toString(),
      sourceKind: sig.sourceKind,
      sourceId: sig.sourceId,
      title: `Agent Execution Blocker: ${sig.sourceKind}`,
      description: `Failed with state ${sig.state}, hash: ${sig.payloadHash}`,
      state: sig.state,
      severity: "CRITICAL",
      sourceRef: { kind: "agent_db", ref: `agent.${sig.sourceKind}:${sig.sourceId}` },
      actionUrl: `/agent/workforce/${sig.sourceKind}/${sig.sourceId}`,
      createdAt: sig.receivedAt.toISOString(),
      observedAt: sig.observedAt.toISOString(),
    });
  }

  return mvpList(blockers, [
    { kind: "company_db", ref: "operating.task_dependencies" },
    { kind: "agent_db", ref: "operating.runtime_source_signals" },
  ]);
}

export async function getWorkInspectorService(
  ctx: TenantContext,
  sourceKind: string,
  sourceId: string
): Promise<MvpSuccess<RuntimeItemDetail>> {
  const wsId = BigInt(ctx.workspaceId);

  // Check if it is a company task
  if (sourceKind === "company_db" || sourceKind === "task") {
    const taskId = BigInt(sourceId);
    const [t] = await db
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)));

    if (!t) throw APIError.notFound("Task not found");

    return mvpItem(
      {
        id: `task_${t.id}`,
        workspaceId: ctx.workspaceId.toString(),
        sourceKind: "company_db",
        sourceId: t.id.toString(),
        title: t.title,
        description: t.description,
        state: t.status,
        severity: "MEDIUM",
        sourceRef: { kind: "company_db", ref: `operating.tasks:${t.id}` },
        actionUrl: `/operations/tasks/${t.id}`,
        createdAt: t.createdAt.toISOString(),
        observedAt: t.updatedAt.toISOString(),
        payload: { priority: t.priority, projectId: t.projectId?.toString() },
        dependencies: [],
      },
      [{ kind: "company_db", ref: `operating.tasks:${t.id}` }]
    );
  }

  // Check if it is an agent signal projection
  const [sig] = await db
    .select()
    .from(runtimeSourceSignals)
    .where(
      and(
        eq(runtimeSourceSignals.workspaceId, wsId),
        eq(runtimeSourceSignals.sourceKind, sourceKind),
        eq(runtimeSourceSignals.sourceId, sourceId)
      )
    )
    .orderBy(desc(runtimeSourceSignals.observedAt));

  if (!sig) {
    throw APIError.notFound("Runtime item not found");
  }

  return mvpItem(
    {
      id: `sig_${sig.id}`,
      workspaceId: ctx.workspaceId.toString(),
      sourceKind: sig.sourceKind,
      sourceId: sig.sourceId,
      title: `Agent Runtime Item (${sig.sourceKind})`,
      description: `State: ${sig.state}`,
      state: sig.state,
      severity: "HIGH",
      sourceRef: { kind: "agent_db", ref: `agent.${sig.sourceKind}:${sig.sourceId}` },
      actionUrl: `/agent/workforce/${sig.sourceKind}/${sig.sourceId}`,
      createdAt: sig.receivedAt.toISOString(),
      observedAt: sig.observedAt.toISOString(),
      payload: { correlationId: sig.correlationId, payloadHash: sig.payloadHash },
      dependencies: [],
    },
    [{ kind: "agent_db", ref: `agent.${sig.sourceKind}:${sig.sourceId}` }]
  );
}

export async function snoozeRuntimeItemService(
  ctx: TenantContext,
  sourceKind: string,
  sourceId: string,
  snoozedUntilIso: string
): Promise<MvpSuccess<{ snoozed: boolean }>> {
  if (!ctx.memberId) {
    throw APIError.unauthenticated("Actor member identity required to snooze");
  }

  const wsId = BigInt(ctx.workspaceId);
  const actorMemberId = BigInt(ctx.memberId);
  const snoozedUntil = new Date(snoozedUntilIso);
  const now = new Date();

  const [existing] = await db
    .select()
    .from(runtimeSnoozes)
    .where(
      and(
        eq(runtimeSnoozes.workspaceId, wsId),
        eq(runtimeSnoozes.actorMemberId, actorMemberId),
        eq(runtimeSnoozes.sourceKind, sourceKind),
        eq(runtimeSnoozes.sourceId, sourceId)
      )
    );

  if (existing) {
    await db
      .update(runtimeSnoozes)
      .set({ snoozedUntil, updatedAt: now })
      .where(eq(runtimeSnoozes.id, existing.id));
  } else {
    await db.insert(runtimeSnoozes).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      actorMemberId,
      sourceKind,
      sourceId,
      snoozedUntil,
      createdAt: now,
      updatedAt: now,
    });
  }

  return mvpItem({ snoozed: true }, [{ kind: "company_db", ref: "operating.runtime_snoozes" }]);
}

export async function getSourceStatusService(ctx: TenantContext): Promise<MvpSuccess<readonly SourceStatus[]>> {
  const now = new Date().toISOString();
  return mvpList(
    [
      {
        sourceKind: "company_db",
        plane: "company",
        status: "HEALTHY",
        lastObservedAt: now,
      },
      {
        sourceKind: "agent_db",
        plane: "agent",
        status: "HEALTHY",
        lastObservedAt: now,
      },
      {
        sourceKind: "control_plane",
        plane: "platform",
        status: "HEALTHY",
        lastObservedAt: now,
      },
    ],
    [{ kind: "company_db", ref: "operating.runtime_source_signals" }]
  );
}
