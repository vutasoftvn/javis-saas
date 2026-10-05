import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { computeKeyResultProgress, KrScoringType } from "./okr-scoring.service";

const { okrObjectives, keyResults, projects } = schema;

export interface GoalStats {
  objectiveCount: number;
  krTotal: number;
  krAchieved: number;
}

/**
 * objectiveId → goalId hiệu lực.
 * - Objective công ty: chính `goal_id`.
 * - Objective dự án: goal của objective công ty cha; cha lấy từ `parent_objective_id`,
 *   nếu NULL thì từ `projects.objective_id` (thừa kế). Không có cha thì không thuộc goal nào.
 */
export async function loadObjectiveGoalMap(wsId: bigint): Promise<Map<string, string>> {
  const rows = await db
    .select({
      id: okrObjectives.id,
      scope: okrObjectives.scope,
      goalId: okrObjectives.goalId,
      parentObjectiveId: okrObjectives.parentObjectiveId,
      projectObjectiveId: projects.objectiveId,
    })
    .from(okrObjectives)
    .leftJoin(
      projects,
      and(eq(projects.id, okrObjectives.projectId), eq(projects.workspaceId, okrObjectives.workspaceId)),
    )
    .where(and(eq(okrObjectives.workspaceId, wsId), isNull(okrObjectives.deletedAt)));

  const companyGoal = new Map<string, string>();
  for (const r of rows) {
    if (r.scope === "company" && r.goalId) companyGoal.set(r.id.toString(), r.goalId.toString());
  }

  const result = new Map<string, string>();
  for (const r of rows) {
    const id = r.id.toString();
    if (r.scope === "company") {
      const g = companyGoal.get(id);
      if (g) result.set(id, g);
      continue;
    }
    const parent = r.parentObjectiveId ?? r.projectObjectiveId;
    const g = parent ? companyGoal.get(parent.toString()) : undefined;
    if (g) result.set(id, g);
  }
  return result;
}

export async function loadGoalStats(wsId: bigint): Promise<Map<string, GoalStats>> {
  const goalOf = await loadObjectiveGoalMap(wsId);
  const stats = new Map<string, GoalStats>();
  const bucket = (goalId: string): GoalStats => {
    let s = stats.get(goalId);
    if (!s) {
      s = { objectiveCount: 0, krTotal: 0, krAchieved: 0 };
      stats.set(goalId, s);
    }
    return s;
  };

  for (const goalId of goalOf.values()) bucket(goalId).objectiveCount += 1;

  const krs = await db
    .select()
    .from(keyResults)
    .where(and(eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)));

  for (const kr of krs) {
    const goalId = goalOf.get(kr.objectiveId.toString());
    if (!goalId) continue;
    const s = bucket(goalId);
    s.krTotal += 1;
    const progress = computeKeyResultProgress({
      baseline: kr.baselineValue,
      target: kr.targetValue,
      current: kr.currentValue,
      scoringType: kr.scoringType as KrScoringType,
    });
    if (progress !== null && progress >= 1) s.krAchieved += 1;
  }
  return stats;
}
