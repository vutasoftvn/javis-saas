import { randomUUID } from "node:crypto";
import { and, desc, eq, inArray, isNull } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../models/db";
import {
  executionPlans,
  executionPlanItems,
  projects,
  tasks,
  taskProjects,
  taskDependencies,
  weeklyCommitments,
  workspaceCapabilityPolicy,
} from "../../shared/db/schema/operations";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import type { TenantContext } from "../../shared/types/tenant_context";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { EXECUTION_PLAN_ACCEPTED } from "../../shared/events";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  ensureAiWorkforceMember,
  resolveFounderMemberId,
  OwnerAgentProfile,
} from "./ai-member.service";
import {
  classifyItem,
  routeOwnerProfile,
  validateFounderOverride,
  AutonomyClass,
  CapabilityRisk,
  TenantPolicyDecision,
} from "./autonomy-classifier";

export interface CreatePlanItemInput {
  title: string;
  decisionReason: string;
  evidenceRefs: string[];
  suggestedDomain: string | null;
  expectedCapability: string | null;
  capabilityRisk: CapabilityRisk | null;
  tenantPolicyDecision: TenantPolicyDecision | null;
  dependsOnTitles: string[];
  priority?: "low" | "medium" | "high" | "urgent";
}

export interface CreateExecutionPlanInput {
  workspaceId: string;
  projectId: string;
  weeklyPlanId: string | null;
  goalText: string;
  origin: "command_center" | "chat";
  originRef: string | null;
  runId: string | null;
  items: CreatePlanItemInput[];
}

export interface ExecutionPlanItemView {
  id: string;
  title: string;
  decisionReason: string;
  evidenceRefs: string[];
  ownerAgentProfile: string | null;
  expectedCapability: string | null;
  autonomyClass: AutonomyClass;
  autonomyClassSource: string;
  priority: string;
  dependsOnItemIds: string[];
  status: string;
  materializedTaskId: string | null;
}

export interface ExecutionPlanView {
  id: string;
  workspaceId: string;
  projectId: string;
  weeklyPlanId: string | null;
  goalText: string;
  status: string;
  origin: string;
  originRef: string | null;
  runId: string | null;
  items: ExecutionPlanItemView[];
  createdAt: string;
  updatedAt: string;
}

export interface PatchPlanItemInput {
  title?: string;
  evidenceRefs?: string[];
  priority?: "low" | "medium" | "high" | "urgent";
  autonomyClass?: AutonomyClass;
  ownerAgentProfile?: string | null;
  drop?: boolean;
}

type ItemRow = typeof executionPlanItems.$inferSelect;
type PlanRow = typeof executionPlans.$inferSelect;

function toItemView(row: ItemRow): ExecutionPlanItemView {
  return {
    id: row.id.toString(),
    title: row.title,
    decisionReason: row.decisionReason,
    evidenceRefs: Array.isArray(row.evidenceRefs) ? (row.evidenceRefs as string[]) : [],
    ownerAgentProfile: row.ownerAgentProfile,
    expectedCapability: row.expectedCapability,
    autonomyClass: row.autonomyClass as AutonomyClass,
    autonomyClassSource: row.autonomyClassSource,
    priority: row.priority ?? "medium",
    dependsOnItemIds: Array.isArray(row.dependsOnItemIds)
      ? (row.dependsOnItemIds as unknown[]).map((v) => String(v))
      : [],
    status: row.status,
    materializedTaskId: row.materializedTaskId ? row.materializedTaskId.toString() : null,
  };
}

function toPlanView(plan: PlanRow, items: ItemRow[]): ExecutionPlanView {
  return {
    id: plan.id.toString(),
    workspaceId: plan.workspaceId.toString(),
    projectId: plan.projectId.toString(),
    weeklyPlanId: plan.weeklyPlanId ? plan.weeklyPlanId.toString() : null,
    goalText: plan.goalText,
    status: plan.status,
    origin: plan.origin,
    originRef: plan.originRef,
    runId: plan.runId,
    items: items
      .slice()
      .sort((a, b) => (a.sortKey ?? 0) - (b.sortKey ?? 0))
      .map(toItemView),
    createdAt: plan.createdAt.toISOString(),
    updatedAt: plan.updatedAt.toISOString(),
  };
}

/**
 * Tạo Execution Plan nháp từ output đã phân rã của agent. Mỗi item được router
 * + classifier (thuần) gắn owner_agent_profile + autonomy_class. Nếu weeklyPlanId
 * đã có plan 'draft' thì plan cũ chuyển 'superseded' (chỉ 1 draft/weekly_plan).
 */
export async function createExecutionPlanService(
  input: CreateExecutionPlanInput,
  authorization: string | undefined,
  ctxOverride?: TenantContext
): Promise<ExecutionPlanView> {
  const ctx = ctxOverride ?? (await requireWorkspaceAccess(authorization, input.workspaceId));
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(input.projectId);
  const goalText = input.goalText?.trim();
  if (!goalText) throw APIError.invalidArgument("goalText không được rỗng");
  if (!input.items || input.items.length === 0) {
    throw APIError.invalidArgument("plan phải có ít nhất 1 item");
  }

  return await db.transaction(async (tx) => {
    const [proj] = await tx
      .select({ id: projects.id })
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);
    if (!proj) throw APIError.notFound(`project ${input.projectId} not found`);

    if (input.weeklyPlanId) {
      await tx
        .update(executionPlans)
        .set({ status: "superseded", updatedAt: new Date() })
        .where(
          and(
            eq(executionPlans.weeklyPlanId, BigInt(input.weeklyPlanId)),
            eq(executionPlans.workspaceId, wsId),
            eq(executionPlans.status, "draft"),
            isNull(executionPlans.deletedAt)
          )
        );
    }

    const planId = generateSnowflake();
    const [plan] = await tx
      .insert(executionPlans)
      .values({
        id: planId,
        workspaceId: wsId,
        projectId: pId,
        weeklyPlanId: input.weeklyPlanId ? BigInt(input.weeklyPlanId) : null,
        goalText,
        status: "draft",
        origin: input.origin,
        originRef: input.originRef,
        runId: input.runId,
      })
      .returning();

    // WGA #3 — override per-workspace: đọc workspace_capability_policy để đưa
    // vào classifier làm tenant_policy_decision (đè lên default theo risk;
    // FORBIDDEN_RE vẫn thắng ALLOW).
    const policyRows = await tx
      .select({
        capabilityId: workspaceCapabilityPolicy.capabilityId,
        decision: workspaceCapabilityPolicy.decision,
      })
      .from(workspaceCapabilityPolicy)
      .where(eq(workspaceCapabilityPolicy.workspaceId, wsId));
    const policyByCapability = new Map<string, TenantPolicyDecision>(
      policyRows.map((r) => [r.capabilityId, r.decision as TenantPolicyDecision])
    );

    // Pass 1 — tạo item + classify.
    const titleToId = new Map<string, string>();
    const inserted: ItemRow[] = [];
    let idx = 0;
    for (const it of input.items) {
      const title = it.title?.trim();
      if (!title) throw APIError.invalidArgument("item.title không được rỗng");
      const decisionReason = it.decisionReason?.trim();
      if (!decisionReason || decisionReason.length < 5) {
        throw APIError.invalidArgument(`item "${title}": decisionReason tối thiểu 5 ký tự`);
      }

      const effectivePolicyDecision: TenantPolicyDecision | null = it.expectedCapability
        ? policyByCapability.get(it.expectedCapability) ?? it.tenantPolicyDecision
        : it.tenantPolicyDecision;
      const { autonomyClass, source } = classifyItem({
        expectedCapability: it.expectedCapability,
        capabilityRisk: it.capabilityRisk,
        tenantPolicyDecision: effectivePolicyDecision,
      });
      // FOUNDER_ONLY ⟺ không agent nào đảm nhận — luôn để owner_agent_profile = null.
      const ownerAgentProfile =
        autonomyClass === "FOUNDER_ONLY"
          ? null
          : routeOwnerProfile(it.expectedCapability, it.suggestedDomain);

      const itemId = generateSnowflake();
      const [row] = await tx
        .insert(executionPlanItems)
        .values({
          id: itemId,
          planId: plan!.id,
          workspaceId: wsId,
          title,
          decisionReason,
          evidenceRefs: it.evidenceRefs ?? [],
          ownerAgentProfile,
          expectedCapability: it.expectedCapability,
          autonomyClass,
          autonomyClassSource: source,
          priority: it.priority ?? "medium",
          dependsOnItemIds: [],
          sortKey: idx,
        })
        .returning();
      inserted.push(row!);
      titleToId.set(title, itemId.toString());
      idx += 1;
    }

    // Pass 2 — map dependsOnTitles -> sibling item ids.
    for (let i = 0; i < input.items.length; i += 1) {
      const deps = (input.items[i]!.dependsOnTitles ?? [])
        .map((t) => titleToId.get(t.trim()))
        .filter((v): v is string => Boolean(v));
      if (deps.length === 0) continue;
      const row = inserted[i]!;
      await tx
        .update(executionPlanItems)
        .set({ dependsOnItemIds: deps, updatedAt: new Date() })
        .where(eq(executionPlanItems.id, row.id));
      row.dependsOnItemIds = deps;
    }

    return toPlanView(plan!, inserted);
  });
}

export async function listExecutionPlansService(
  p: { workspaceId: string; projectId: string; status?: string },
  authorization: string | undefined
): Promise<ExecutionPlanView[]> {
  const ctx = await requireWorkspaceAccess(authorization, p.workspaceId);
  const wsId = BigInt(ctx.workspaceId);
  const conds = [
    eq(executionPlans.workspaceId, wsId),
    eq(executionPlans.projectId, BigInt(p.projectId)),
    isNull(executionPlans.deletedAt),
  ];
  if (p.status) conds.push(eq(executionPlans.status, p.status));

  const plans = await db
    .select()
    .from(executionPlans)
    .where(and(...conds))
    .orderBy(desc(executionPlans.createdAt));
  if (plans.length === 0) return [];

  const items = await db
    .select()
    .from(executionPlanItems)
    .where(
      inArray(
        executionPlanItems.planId,
        plans.map((pl) => pl.id)
      )
    );
  const byPlan = new Map<string, ItemRow[]>();
  for (const it of items) {
    const k = it.planId.toString();
    (byPlan.get(k) ?? byPlan.set(k, []).get(k)!).push(it);
  }
  return plans.map((pl) => toPlanView(pl, byPlan.get(pl.id.toString()) ?? []));
}

export async function getExecutionPlanService(
  id: string,
  workspaceId: string,
  authorization: string | undefined
): Promise<ExecutionPlanView> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId);
  const wsId = BigInt(ctx.workspaceId);
  const [plan] = await db
    .select()
    .from(executionPlans)
    .where(and(eq(executionPlans.id, BigInt(id)), eq(executionPlans.workspaceId, wsId)))
    .limit(1);
  if (!plan) throw APIError.notFound(`execution plan ${id} not found`);
  const items = await db
    .select()
    .from(executionPlanItems)
    .where(eq(executionPlanItems.planId, plan.id));
  return toPlanView(plan, items);
}

export async function patchExecutionPlanItemService(
  planId: string,
  itemId: string,
  patch: PatchPlanItemInput,
  workspaceId: string,
  authorization: string | undefined
): Promise<ExecutionPlanItemView> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId);
  const wsId = BigInt(ctx.workspaceId);

  return await db.transaction(async (tx) => {
    const [plan] = await tx
      .select()
      .from(executionPlans)
      .where(and(eq(executionPlans.id, BigInt(planId)), eq(executionPlans.workspaceId, wsId)))
      .limit(1);
    if (!plan) throw APIError.notFound(`execution plan ${planId} not found`);
    if (plan.status !== "draft") {
      throw APIError.failedPrecondition("chỉ sửa được item khi plan còn ở trạng thái draft");
    }

    const [item] = await tx
      .select()
      .from(executionPlanItems)
      .where(and(eq(executionPlanItems.id, BigInt(itemId)), eq(executionPlanItems.planId, plan.id)))
      .limit(1);
    if (!item) throw APIError.notFound(`plan item ${itemId} not found`);

    const set: Partial<ItemRow> = { updatedAt: new Date() };

    if (patch.drop === true) {
      set.status = "dropped";
    }
    if (patch.title !== undefined) {
      const t = patch.title.trim();
      if (!t) throw APIError.invalidArgument("title không được rỗng");
      set.title = t;
    }
    if (patch.evidenceRefs !== undefined) {
      set.evidenceRefs = patch.evidenceRefs;
    }
    if (patch.priority !== undefined) {
      set.priority = patch.priority;
    }
    if (patch.ownerAgentProfile !== undefined) {
      set.ownerAgentProfile = patch.ownerAgentProfile;
    }
    if (patch.autonomyClass !== undefined && patch.autonomyClass !== item.autonomyClass) {
      if (patch.autonomyClass === "AUTO") {
        // Chính sách workspace (tenant_policy) đã cấm/yêu-cầu-duyệt capability này
        // lúc classify → founder không được lật ngược lên AUTO ở đây.
        if (item.autonomyClassSource === "tenant_policy") {
          throw APIError.permissionDenied(
            "Chính sách workspace không cho phép AUTO cho capability này — đổi chính sách trước"
          );
        }
        const check = validateFounderOverride("AUTO", {
          expectedCapability: item.expectedCapability,
          capabilityRisk: null,
          // tenant_policy đã được loại trừ ở trên; chỉ còn chặn FORBIDDEN_RE / thiếu capability.
          tenantPolicyDecision: "ALLOW",
        });
        if (!check.ok) throw APIError.permissionDenied(check.reason);
      }
      set.autonomyClass = patch.autonomyClass;
      set.autonomyClassSource = "founder_override";
    }

    const [updated] = await tx
      .update(executionPlanItems)
      .set(set)
      .where(eq(executionPlanItems.id, item.id))
      .returning();
    return toItemView(updated!);
  });
}

export interface AcceptExecutionPlanResult {
  planId: string;
  taskIds: string[];
  founderOnlyTaskIds: string[];
}

const EXECUTION_MODE_BY_CLASS: Record<AutonomyClass, "AGENT" | "HUMAN"> = {
  AUTO: "AGENT",
  NEEDS_APPROVAL: "AGENT",
  FOUNDER_ONLY: "HUMAN",
};

/** DFS phát hiện chu trình trong depends_on giữa các item chưa dropped. */
function assertNoCycles(items: { id: string; deps: string[] }[]): void {
  const graph = new Map<string, string[]>();
  for (const it of items) graph.set(it.id, it.deps);
  const WHITE = 0;
  const GRAY = 1;
  const BLACK = 2;
  const color = new Map<string, number>();
  for (const id of graph.keys()) color.set(id, WHITE);

  const visit = (node: string, path: string[]): void => {
    color.set(node, GRAY);
    for (const next of graph.get(node) ?? []) {
      if (!graph.has(next)) continue; // dep trỏ item đã dropped — bỏ qua
      const c = color.get(next);
      if (c === GRAY) {
        throw APIError.invalidArgument(
          `circular dependency: ${[...path, node, next].join(" -> ")}`
        );
      }
      if (c === WHITE) visit(next, [...path, node]);
    }
    color.set(node, BLACK);
  };

  for (const id of graph.keys()) {
    if (color.get(id) === WHITE) visit(id, []);
  }
}

/**
 * Duyệt cả lô: chuyển plan 'draft' -> 'accepted' và materialize từng item chưa
 * dropped thành weekly_commitments + operating.tasks + task_projects. Item AUTO/
 * NEEDS_APPROVAL gán cho AI member của owner_agent_profile (execution_mode AGENT);
 * FOUNDER_ONLY gán founder member (execution_mode HUMAN). autonomy_class chính xác
 * vẫn nằm ở execution_plan_items — worker task-executor JOIN ngược để đọc.
 */
export async function acceptExecutionPlanService(
  planId: string,
  p: { workspaceId: string; acceptedByMemberId?: string | null },
  authorization: string | undefined
): Promise<AcceptExecutionPlanResult> {
  const ctx = await requireWorkspaceAccess(authorization, p.workspaceId);
  const wsId = BigInt(ctx.workspaceId);

  return await db.transaction(async (tx) => {
    const [plan] = await tx
      .select()
      .from(executionPlans)
      .where(and(eq(executionPlans.id, BigInt(planId)), eq(executionPlans.workspaceId, wsId)))
      .limit(1);
    if (!plan) throw APIError.notFound(`execution plan ${planId} not found`);
    if (plan.status !== "draft") {
      throw APIError.failedPrecondition(`plan không ở trạng thái draft (hiện: ${plan.status})`);
    }
    if (!plan.weeklyPlanId) {
      throw APIError.failedPrecondition(
        "plan chưa gắn weekly_plan — đặt mục tiêu tuần trước khi duyệt kế hoạch"
      );
    }

    const allItems = await tx
      .select()
      .from(executionPlanItems)
      .where(eq(executionPlanItems.planId, plan.id));
    const liveItems = allItems.filter((it) => it.status !== "dropped");
    if (liveItems.length === 0) {
      throw APIError.invalidArgument("plan không còn item nào để duyệt (tất cả đã bỏ)");
    }

    assertNoCycles(
      liveItems.map((it) => ({
        id: it.id.toString(),
        deps: Array.isArray(it.dependsOnItemIds)
          ? (it.dependsOnItemIds as unknown[]).map((v) => String(v))
          : [],
      }))
    );

    const founderMemberId = await resolveFounderMemberId(
      tx,
      ctx.workspaceId,
      p.acceptedByMemberId ?? ctx.workforceMemberId ?? null
    );
    const aiMemberByProfile = new Map<OwnerAgentProfile, string>();
    const ensureAi = async (profile: OwnerAgentProfile): Promise<string> => {
      const cached = aiMemberByProfile.get(profile);
      if (cached) return cached;
      const id = await ensureAiWorkforceMember(tx, ctx.workspaceId, profile);
      aiMemberByProfile.set(profile, id);
      return id;
    };

    const itemIdToTaskId = new Map<string, string>();
    const taskIds: string[] = [];
    const founderOnlyTaskIds: string[] = [];

    for (const it of liveItems) {
      const klass = it.autonomyClass as AutonomyClass;
      const executionMode = EXECUTION_MODE_BY_CLASS[klass];

      let assigneeMemberId: bigint | null = null;
      if (klass === "FOUNDER_ONLY") {
        assigneeMemberId = founderMemberId ? BigInt(founderMemberId) : null;
      } else {
        const profile = (it.ownerAgentProfile as OwnerAgentProfile | null) ?? "operations";
        assigneeMemberId = BigInt(await ensureAi(profile));
      }

      const [commitment] = await tx
        .insert(weeklyCommitments)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          weeklyPlanId: plan.weeklyPlanId,
          initiativeId: null,
          title: it.title.slice(0, 255),
          commitmentOwnerType: klass === "FOUNDER_ONLY" ? "FOUNDER" : "AGENT",
          executionMode,
        })
        .returning();

      const taskId = generateSnowflake();
      await tx.insert(tasks).values({
        id: taskId,
        workspaceId: wsId,
        title: it.title,
        status: "todo",
        priority: it.priority ?? "medium",
        source: "ai_agent_proposal",
        weeklyCommitmentId: commitment!.id,
        assigneeMemberId,
        executionMode,
      });

      await tx
        .insert(taskProjects)
        .values({ workspaceId: wsId, taskId, projectId: plan.projectId })
        .onConflictDoNothing();

      await tx
        .update(executionPlanItems)
        .set({ materializedTaskId: taskId, status: "accepted", updatedAt: new Date() })
        .where(eq(executionPlanItems.id, it.id));

      itemIdToTaskId.set(it.id.toString(), taskId.toString());
      taskIds.push(taskId.toString());
      if (klass === "FOUNDER_ONLY") founderOnlyTaskIds.push(taskId.toString());
    }

    // Pass 2 — dựng task_dependencies từ depends_on_item_ids. Kiểm tra chu trình
    // trên TOÀN graph task_dependencies của workspace (không chỉ trong plan này)
    // — phòng cạnh mà accept plan thứ 2 tạo cạnh khép vòng với task của plan cũ.
    // task_dependencies không có workspace_id — join tasks để chỉ lấy cạnh của
    // workspace này (nếu không sẽ gộp graph của MỌI workspace, false-positive).
    const existingDeps = await tx
      .select({ taskId: taskDependencies.taskId, dependsOnTaskId: taskDependencies.dependsOnTaskId })
      .from(taskDependencies)
      .innerJoin(tasks, eq(tasks.id, taskDependencies.taskId))
      .where(and(eq(tasks.workspaceId, wsId), isNull(taskDependencies.deletedAt)));
    const adj = new Map<string, Set<string>>();
    const addEdge = (from: string, to: string): void => {
      (adj.get(from) ?? adj.set(from, new Set()).get(from)!).add(to);
    };
    for (const d of existingDeps) {
      addEdge(d.taskId.toString(), d.dependsOnTaskId.toString());
    }

    const newEdges: Array<{ taskId: string; depTaskId: string }> = [];
    for (const it of liveItems) {
      const deps = Array.isArray(it.dependsOnItemIds)
        ? (it.dependsOnItemIds as unknown[]).map((v) => String(v))
        : [];
      const taskId = itemIdToTaskId.get(it.id.toString());
      if (!taskId) continue;
      for (const depItemId of deps) {
        const depTaskId = itemIdToTaskId.get(depItemId);
        if (!depTaskId) continue; // dep trỏ item đã dropped
        newEdges.push({ taskId, depTaskId });
        addEdge(taskId, depTaskId);
      }
    }

    // DFS phát hiện chu trình trên graph đã gộp cạnh mới.
    const WHITE = 0;
    const GRAY = 1;
    const BLACK = 2;
    const color = new Map<string, number>();
    const dfs = (node: string): void => {
      color.set(node, GRAY);
      for (const next of adj.get(node) ?? []) {
        const c = color.get(next) ?? WHITE;
        if (c === GRAY) throw APIError.invalidArgument(`circular task dependency involving ${next}`);
        if (c === WHITE) dfs(next);
      }
      color.set(node, BLACK);
    };
    for (const node of adj.keys()) {
      if ((color.get(node) ?? WHITE) === WHITE) dfs(node);
    }

    for (const e of newEdges) {
      await tx.insert(taskDependencies).values({
        id: generateSnowflake(),
        taskId: BigInt(e.taskId),
        dependsOnTaskId: BigInt(e.depTaskId),
        dependencyType: "BLOCKS",
        status: "PENDING",
      });
    }

    await tx
      .update(executionPlans)
      .set({
        status: "accepted",
        acceptedByMemberId: founderMemberId ? BigInt(founderMemberId) : null,
        acceptedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(executionPlans.id, plan.id));

    const event = makeBusinessEvent({
      eventType: EXECUTION_PLAN_ACCEPTED,
      workspaceId: ctx.workspaceId,
      aggregateType: "execution_plan",
      aggregateId: plan.id.toString(),
      correlationId: randomUUID(),
      actor: { kind: "user", id: ctx.userId || "0" },
      classification: "internal",
      payload: {
        workspaceId: ctx.workspaceId,
        projectId: plan.projectId.toString(),
        planId: plan.id.toString(),
        taskIds,
      },
    });
    await appendOutboxEvent(tx, event);

    return { planId: plan.id.toString(), taskIds, founderOnlyTaskIds };
  });
}

export interface CapabilityPolicyEntry {
  capabilityId: string;
  decision: TenantPolicyDecision;
}

export async function listCapabilityPolicyService(
  workspaceId: string,
  authorization: string | undefined
): Promise<CapabilityPolicyEntry[]> {
  await requireWorkspaceAccess(authorization, workspaceId);
  const rows = await db
    .select({
      capabilityId: workspaceCapabilityPolicy.capabilityId,
      decision: workspaceCapabilityPolicy.decision,
    })
    .from(workspaceCapabilityPolicy)
    .where(eq(workspaceCapabilityPolicy.workspaceId, BigInt(workspaceId)));
  return rows.map((r) => ({
    capabilityId: r.capabilityId,
    decision: r.decision as TenantPolicyDecision,
  }));
}

export async function setCapabilityPolicyService(
  p: { workspaceId: string; capabilityId: string; decision: TenantPolicyDecision | null },
  ctx: TenantContext
): Promise<CapabilityPolicyEntry[]> {
  const wsId = BigInt(p.workspaceId);
  const cap = p.capabilityId?.trim();
  if (!cap) throw APIError.invalidArgument("capabilityId không được rỗng");

  if (p.decision === null) {
    await db
      .delete(workspaceCapabilityPolicy)
      .where(
        and(
          eq(workspaceCapabilityPolicy.workspaceId, wsId),
          eq(workspaceCapabilityPolicy.capabilityId, cap)
        )
      );
  } else {
    if (!["ALLOW", "REQUIRE_APPROVAL", "DENY"].includes(p.decision)) {
      throw APIError.invalidArgument("decision phải là ALLOW | REQUIRE_APPROVAL | DENY | null");
    }
    await db
      .insert(workspaceCapabilityPolicy)
      .values({
        workspaceId: wsId,
        capabilityId: cap,
        decision: p.decision,
        updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: [workspaceCapabilityPolicy.workspaceId, workspaceCapabilityPolicy.capabilityId],
        set: {
          decision: p.decision,
          updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
          updatedAt: new Date(),
        },
      });
  }
  const rows = await db
    .select({
      capabilityId: workspaceCapabilityPolicy.capabilityId,
      decision: workspaceCapabilityPolicy.decision,
    })
    .from(workspaceCapabilityPolicy)
    .where(eq(workspaceCapabilityPolicy.workspaceId, wsId));
  return rows.map((r) => ({
    capabilityId: r.capabilityId,
    decision: r.decision as TenantPolicyDecision,
  }));
}

export async function rejectExecutionPlanService(
  planId: string,
  workspaceId: string,
  authorization: string | undefined
): Promise<void> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId);
  const wsId = BigInt(ctx.workspaceId);
  const res = await db
    .update(executionPlans)
    .set({ status: "rejected", updatedAt: new Date() })
    .where(
      and(
        eq(executionPlans.id, BigInt(planId)),
        eq(executionPlans.workspaceId, wsId),
        eq(executionPlans.status, "draft")
      )
    )
    .returning({ id: executionPlans.id });
  if (res.length === 0) {
    throw APIError.failedPrecondition("plan không tồn tại hoặc không ở trạng thái draft");
  }
}
