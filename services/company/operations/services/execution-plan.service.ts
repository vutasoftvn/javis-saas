import { and, desc, eq, inArray, isNull } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../models/db";
import { executionPlans, executionPlanItems, projects } from "../../shared/db/schema/operations";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
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
  authorization: string | undefined
): Promise<ExecutionPlanView> {
  const ctx = await requireWorkspaceAccess(authorization, input.workspaceId);
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

      const { autonomyClass, source } = classifyItem({
        expectedCapability: it.expectedCapability,
        capabilityRisk: it.capabilityRisk,
        tenantPolicyDecision: it.tenantPolicyDecision,
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
