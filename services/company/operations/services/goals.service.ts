import { APIError } from "encore.dev/api";
import { eq, and, sql, desc, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getCadenceStatusService } from "./onboard.service";

const { goals, objectives, cosaKeyResults, onboardSnapshots, projects } = schema;

export type GoalType = "vision" | "strategic" | "tactical" | "sprint";
export type GoalStatus = "draft" | "active" | "completed" | "abandoned";

export interface GoalTreeNode {
  id: string;
  parentId: string | null;
  workspaceId: string;
  title: string;
  description: string | null;
  goalType: GoalType;
  status: GoalStatus;
  startDate: string | null;
  endDate: string | null;
  durationWeeks: number | null;
  onboardSnapshotId: string | null;
  depth: number;
  hierarchy: string;
  objectiveCount: number;
  krTotal: number;
  krAchieved: number;
  children: GoalTreeNode[];
}

// Mọi id do caller gửi lên (goal cha, goal, objective, KR) phải thuộc đúng
// workspace đã được guard ở handler — nếu không, caller có quyền ở workspace A
// có thể sửa dữ liệu workspace B chỉ bằng cách gửi id của B.
async function assertGoalInWorkspace(wsId: bigint, goalId: bigint): Promise<void> {
  const [row] = await db
    .select({ id: goals.id })
    .from(goals)
    .where(and(eq(goals.id, goalId), eq(goals.workspaceId, wsId)))
    .limit(1);
  if (!row) {
    throw APIError.notFound("Không tìm thấy Goal trong workspace này.");
  }
}

export async function assertObjectiveInWorkspace(wsId: bigint, objectiveId: bigint): Promise<void> {
  const [row] = await db
    .select({ id: objectives.id })
    .from(objectives)
    .where(and(eq(objectives.id, objectiveId), eq(objectives.workspaceId, wsId)))
    .limit(1);
  if (!row) {
    throw APIError.notFound("Không tìm thấy Objective trong workspace này.");
  }
}

export async function createGoalService(params: {
  workspaceId: string;
  parentId?: string;
  title: string;
  description?: string;
  goalType: GoalType;
  startDate?: string;
  endDate?: string;
  durationWeeks?: number;
  status?: GoalStatus;
  snapshotId?: string;
}): Promise<{
  goalId: string;
  onboardSnapshotId: string | null;
  cadenceWarnings: Array<{ dimension: string; urgency: string; message: string }>;
}> {
  const wsId = BigInt(params.workspaceId);
  const goalId = generateSnowflake();

  // Validate dates: cả hai phải cùng NULL hoặc cùng NOT NULL
  if ((params.startDate && !params.endDate) || (!params.startDate && params.endDate)) {
    throw APIError.invalidArgument("start_date và end_date phải cùng có hoặc cùng để trống.");
  }

  if (params.parentId) {
    await assertGoalInWorkspace(wsId, BigInt(params.parentId));
  }

  // 1. Kiểm tra cadence các chiều 'fast' (stage_scale, challenges)
  const cadenceStatus = await getCadenceStatusService(params.workspaceId);
  const cadenceWarnings: Array<{ dimension: string; urgency: string; message: string }> = [];

  // Chỉ 2 chiều Fast quyết định ngữ cảnh khi đặt mục tiêu (plan Startup OS Task 2.2).
  const fastDimensions = new Set(["stage_scale", "challenges"]);
  for (const c of cadenceStatus.cadences) {
    if (!fastDimensions.has(c.dimension)) continue;
    if (c.urgency === "critical" || c.urgency === "recommended") {
      cadenceWarnings.push({
        dimension: c.dimension,
        urgency: c.urgency,
        message: c.neverReviewed
          ? `Chiều ${c.dimension} chưa từng được ghi nhận. Nên cập nhật trước khi tạo mục tiêu.`
          : `Chiều ${c.dimension} đã ${c.daysSinceLastReview} ngày chưa cập nhật (mức độ: ${c.urgency}). Nên cập nhật trước khi tạo mục tiêu.`,
      });
    }
  }

  // 2. Tự động lấy snapshot hiện tại nếu chưa truyền
  let snapshotId = params.snapshotId ? BigInt(params.snapshotId) : null;
  if (!snapshotId) {
    const [currentSnapshot] = await db
      .select({ id: onboardSnapshots.id })
      .from(onboardSnapshots)
      .where(and(eq(onboardSnapshots.workspaceId, wsId), eq(onboardSnapshots.isCurrent, true)))
      .limit(1);

    if (currentSnapshot) {
      snapshotId = currentSnapshot.id;
    }
  }

  await db.insert(goals).values({
    id: goalId,
    workspaceId: wsId,
    parentId: params.parentId ? BigInt(params.parentId) : null,
    title: params.title,
    description: params.description,
    goalType: params.goalType,
    startDate: params.startDate,
    endDate: params.endDate,
    durationWeeks: params.durationWeeks ? String(params.durationWeeks) : null,
    status: params.status || "active",
    onboardSnapshotId: snapshotId,
  });

  return {
    goalId: goalId.toString(),
    onboardSnapshotId: snapshotId ? snapshotId.toString() : null,
    cadenceWarnings,
  };
}

export async function getGoalTreeService(workspaceId: string): Promise<{ tree: GoalTreeNode[] }> {
  const wsId = BigInt(workspaceId);

  // Lấy toàn bộ goals của workspace
  const goalRows = await db
    .select()
    .from(goals)
    .where(eq(goals.workspaceId, wsId));

  // Lấy metrics thống kê cho từng goal (số objectives, tổng KRs, số KRs đạt)
  const statsRows = await db
    .select({
      goalId: objectives.goalId,
      objectiveCount: sql<number>`count(distinct ${objectives.id})::int`,
      krTotal: sql<number>`count(${cosaKeyResults.id})::int`,
      krAchieved: sql<number>`count(case when ${cosaKeyResults.currentValue} >= ${cosaKeyResults.target} then 1 end)::int`,
    })
    .from(objectives)
    .leftJoin(cosaKeyResults, eq(objectives.id, cosaKeyResults.objectiveId))
    .where(eq(objectives.workspaceId, wsId))
    .groupBy(objectives.goalId);

  const statsMap = new Map<string, { objectiveCount: number; krTotal: number; krAchieved: number }>();
  for (const s of statsRows) {
    statsMap.set(s.goalId.toString(), {
      objectiveCount: s.objectiveCount || 0,
      krTotal: s.krTotal || 0,
      krAchieved: s.krAchieved || 0,
    });
  }

  // Xây dựng cây đệ quy
  const nodeMap = new Map<string, GoalTreeNode>();
  for (const g of goalRows) {
    const idStr = g.id.toString();
    const st = statsMap.get(idStr) || { objectiveCount: 0, krTotal: 0, krAchieved: 0 };
    nodeMap.set(idStr, {
      id: idStr,
      parentId: g.parentId ? g.parentId.toString() : null,
      workspaceId: g.workspaceId.toString(),
      title: g.title,
      description: g.description,
      goalType: g.goalType as GoalType,
      status: g.status as GoalStatus,
      startDate: g.startDate,
      endDate: g.endDate,
      durationWeeks: g.durationWeeks ? Number(g.durationWeeks) : null,
      onboardSnapshotId: g.onboardSnapshotId ? g.onboardSnapshotId.toString() : null,
      depth: 0,
      hierarchy: g.title,
      objectiveCount: st.objectiveCount,
      krTotal: st.krTotal,
      krAchieved: st.krAchieved,
      children: [],
    });
  }

  const rootNodes: GoalTreeNode[] = [];
  for (const node of nodeMap.values()) {
    const parent = node.parentId ? nodeMap.get(node.parentId) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      rootNodes.push(node);
    }
  }

  // depth/hierarchy tính sau khi dựng xong cây: trước đây gán ngay trong vòng lặp
  // nên Goal con duyệt trước Goal cha nhận depth/hierarchy sai.
  const assignDepth = (node: GoalTreeNode, depth: number, hierarchy: string): void => {
    node.depth = depth;
    node.hierarchy = hierarchy;
    for (const child of node.children) {
      assignDepth(child, depth + 1, `${hierarchy} › ${child.title}`);
    }
  };
  for (const root of rootNodes) {
    assignDepth(root, 0, root.title);
  }

  return { tree: rootNodes };
}

export async function getGoalsNeedingReviewService(workspaceId: string): Promise<{
  goals: Array<{
    goalId: string;
    goalTitle: string;
    goalType: string;
    snapshotAgeDays: number;
    urgency: "high" | "medium" | "low";
  }>;
}> {
  const wsId = BigInt(workspaceId);

  // Tìm snapshot hiện tại
  const [currentSnapshot] = await db
    .select()
    .from(onboardSnapshots)
    .where(and(eq(onboardSnapshots.workspaceId, wsId), eq(onboardSnapshots.isCurrent, true)))
    .limit(1);

  if (!currentSnapshot) {
    return { goals: [] };
  }

  // Lấy các goals active có snapshot khác snapshot hiện tại
  const activeGoals = await db
    .select({
      goal: goals,
      snapshot: onboardSnapshots,
    })
    .from(goals)
    .innerJoin(onboardSnapshots, eq(goals.onboardSnapshotId, onboardSnapshots.id))
    .where(
      and(
        eq(goals.workspaceId, wsId),
        eq(goals.status, "active"),
        sql`${onboardSnapshots.id} != ${currentSnapshot.id}`
      )
    );

  const now = new Date().getTime();
  const result = activeGoals.map(({ goal, snapshot }) => {
    const ageDays = Math.floor((now - new Date(snapshot.capturedAt).getTime()) / 86400000);
    let urgency: "high" | "medium" | "low" = "low";

    if (["sprint", "tactical"].includes(goal.goalType) && ageDays > 14) {
      urgency = "high";
    } else if (goal.goalType === "strategic" && ageDays > 60) {
      urgency = "medium";
    }

    return {
      goalId: goal.id.toString(),
      goalTitle: goal.title,
      goalType: goal.goalType,
      snapshotAgeDays: ageDays,
      urgency,
    };
  });

  return { goals: result };
}

export async function completeGoalService(params: {
  workspaceId: string;
  goalId: string;
  forceCompleteActiveObjectives?: boolean;
}): Promise<{
  success: boolean;
  completedObjectivesCount: number;
  reviewAmbitionPrompt?: string;
}> {
  const wsId = BigInt(params.workspaceId);
  const gId = BigInt(params.goalId);

  await assertGoalInWorkspace(wsId, gId);

  // Kiểm tra xem có objective nào đang active không
  const activeObjs = await db
    .select()
    .from(objectives)
    .where(
      and(
        eq(objectives.goalId, gId),
        eq(objectives.workspaceId, wsId),
        eq(objectives.status, "active")
      )
    );

  if (activeObjs.length > 0 && !params.forceCompleteActiveObjectives) {
    throw APIError.failedPrecondition(
      `Không thể hoàn thành Goal vì còn ${activeObjs.length} objective đang hoạt động. Hãy hoàn thành các objective trước hoặc chọn hoàn thành bắt buộc.`
    );
  }

  const now = new Date();

  // 1. Cập nhật goal status sang completed
  await db
    .update(goals)
    .set({
      status: "completed",
      completedAt: now,
    })
    .where(and(eq(goals.id, gId), eq(goals.workspaceId, wsId)));

  // 2. Cascade hoàn thành các objective con
  if (activeObjs.length > 0) {
    await db
      .update(objectives)
      .set({ status: "completed" })
      .where(and(eq(objectives.goalId, gId), eq(objectives.workspaceId, wsId)));
  }

  // 3. Cascade cập nhật KRs con: nếu đạt -> achieved, nếu chưa -> missed
  await db.execute(sql`
    UPDATE strategy.cosa_key_results kr
    SET status = CASE WHEN kr.current_value >= kr.target THEN 'achieved' ELSE 'missed' END
    FROM strategy.objectives o
    WHERE kr.objective_id = o.id AND o.goal_id = ${gId} AND o.workspace_id = ${wsId}
      AND kr.status = 'active'
  `);

  return {
    success: true,
    completedObjectivesCount: activeObjs.length,
    reviewAmbitionPrompt: "Mục tiêu chiến lược đã hoàn thành. Hãy kiểm tra lại tham vọng (Goals & Ambition) để chuẩn bị cho chu kỳ tiếp theo.",
  };
}

export async function createObjectiveService(params: {
  workspaceId: string;
  goalId: string;
  title: string;
  description?: string;
  ownerUserId?: string;
  weight?: number;
  displayOrder?: number;
}): Promise<{ objectiveId: string }> {
  const wsId = BigInt(params.workspaceId);
  const gId = BigInt(params.goalId);
  await assertGoalInWorkspace(wsId, gId);
  const objId = generateSnowflake();

  await db.insert(objectives).values({
    id: objId,
    goalId: gId,
    workspaceId: wsId,
    title: params.title,
    description: params.description,
    ownerUserId: params.ownerUserId ? BigInt(params.ownerUserId) : null,
    weight: params.weight !== undefined ? String(params.weight) : "1.0",
    displayOrder: params.displayOrder || 0,
    status: "active",
    progressPct: "0",
  });

  return { objectiveId: objId.toString() };
}

export async function addKeyResultService(params: {
  workspaceId: string;
  objectiveId: string;
  metricName: string;
  baseline?: number;
  target: number;
  unit?: string;
  displayOrder?: number;
}): Promise<{ keyResultId: string }> {
  const objId = BigInt(params.objectiveId);
  await assertObjectiveInWorkspace(BigInt(params.workspaceId), objId);
  const krId = generateSnowflake();

  await db.insert(cosaKeyResults).values({
    id: krId,
    objectiveId: objId,
    metricName: params.metricName,
    baseline: params.baseline !== undefined ? String(params.baseline) : null,
    target: String(params.target),
    currentValue: "0",
    unit: params.unit,
    status: "active",
    displayOrder: params.displayOrder || 0,
  });

  return { keyResultId: krId.toString() };
}

export async function updateKeyResultValueService(params: {
  workspaceId: string;
  keyResultId: string;
  currentValue: number;
}): Promise<{ keyResultId: string; objectiveProgressPct: number }> {
  const krId = BigInt(params.keyResultId);

  // KR không có cột workspace_id — xác định tenant qua objective cha.
  const [joined] = await db
    .select({ kr: cosaKeyResults })
    .from(cosaKeyResults)
    .innerJoin(objectives, eq(objectives.id, cosaKeyResults.objectiveId))
    .where(
      and(eq(cosaKeyResults.id, krId), eq(objectives.workspaceId, BigInt(params.workspaceId)))
    )
    .limit(1);
  const kr = joined?.kr;

  if (!kr) {
    throw APIError.notFound("Không tìm thấy Key Result.");
  }

  const target = Number(kr.target);
  const isAchieved = params.currentValue >= target;

  await db
    .update(cosaKeyResults)
    .set({
      currentValue: String(params.currentValue),
      status: isAchieved ? "achieved" : "active",
    })
    .where(eq(cosaKeyResults.id, krId));

  // Tính lại tiến độ của Objective
  const krs = await db
    .select()
    .from(cosaKeyResults)
    .where(eq(cosaKeyResults.objectiveId, kr.objectiveId));

  let totalPct = 0;
  for (const item of krs) {
    const t = Number(item.target);
    const c = item.id === krId ? params.currentValue : Number(item.currentValue || 0);
    const b = Number(item.baseline || 0);

    let pct = 0;
    if (t > b) {
      pct = Math.min(100, Math.max(0, ((c - b) / (t - b)) * 100));
    } else if (t === b) {
      pct = c >= t ? 100 : 0;
    }
    totalPct += pct;
  }

  const avgPct = krs.length > 0 ? totalPct / krs.length : 0;

  await db
    .update(objectives)
    .set({ progressPct: String(avgPct.toFixed(2)) })
    .where(eq(objectives.id, kr.objectiveId));

  return {
    keyResultId: krId.toString(),
    objectiveProgressPct: Number(avgPct.toFixed(2)),
  };
}
