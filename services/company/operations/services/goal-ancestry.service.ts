import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";

const { initiatives, keyResults, okrObjectives, projects, goals } = schema;

const MAX_GOAL_DEPTH = 8;

export interface GoalAncestryGoal { id: string; title: string; goalType: string }
export interface GoalAncestry {
  resolvedVia: "initiative" | "key_result" | "project" | "none";
  project: { id: string; title: string } | null;
  keyResult: {
    id: string; title: string | null;
    baselineValue: number | null; targetValue: number | null; currentValue: number | null; unit: string | null;
  } | null;
  objective: { id: string; title: string; scope: "company" | "project" } | null;
  companyObjective: { id: string; title: string } | null;
  goalChain: GoalAncestryGoal[];
  unlinkedReason: string | null;
}
export interface GoalAncestryInput {
  projectId: bigint;
  initiativeId: bigint | null;
  keyResultId: bigint | null;
}

const EMPTY: GoalAncestry = {
  resolvedVia: "none", project: null, keyResult: null, objective: null,
  companyObjective: null, goalChain: [], unlinkedReason: null,
};

async function loadObjective(wsId: bigint, id: bigint) {
  const [row] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, id), eq(okrObjectives.workspaceId, wsId), isNull(okrObjectives.deletedAt)))
    .limit(1);
  return row;
}

async function loadGoalChain(wsId: bigint, goalId: bigint): Promise<GoalAncestryGoal[]> {
  const chain: GoalAncestryGoal[] = [];
  const seen = new Set<string>();
  let current: bigint | null = goalId;
  while (current !== null && chain.length < MAX_GOAL_DEPTH) {
    const key = current.toString();
    if (seen.has(key)) break;
    seen.add(key);
    const [g] = await db
      .select({ id: goals.id, title: goals.title, goalType: goals.goalType, parentId: goals.parentId })
      .from(goals)
      .where(and(eq(goals.id, current), eq(goals.workspaceId, wsId)))
      .limit(1);
    if (!g) break;
    chain.push({ id: g.id.toString(), title: g.title, goalType: g.goalType });
    current = g.parentId;
  }
  return chain;
}

export async function resolveGoalAncestry(wsId: bigint, input: GoalAncestryInput): Promise<GoalAncestry> {
  const [project] = await db
    .select({ id: projects.id, title: projects.title, objectiveId: projects.objectiveId, linkStatus: projects.linkStatus })
    .from(projects)
    .where(and(eq(projects.id, input.projectId), eq(projects.workspaceId, wsId), isNull(projects.deletedAt)))
    .limit(1);
  if (!project) return { ...EMPTY, unlinkedReason: "project_not_found" };

  const result: GoalAncestry = {
    ...EMPTY,
    project: { id: project.id.toString(), title: project.title },
  };

  // Bậc 1-2: initiative -> KR, hoặc KR trực tiếp.
  let krId: bigint | null = input.keyResultId;
  let via: GoalAncestry["resolvedVia"] = krId ? "key_result" : "none";
  if (input.initiativeId) {
    const [ini] = await db
      .select({ keyResultId: initiatives.keyResultId })
      .from(initiatives)
      .where(and(eq(initiatives.id, input.initiativeId), eq(initiatives.workspaceId, wsId), isNull(initiatives.deletedAt)))
      .limit(1);
    if (ini) { krId = ini.keyResultId; via = "initiative"; }
  }

  let objective: Awaited<ReturnType<typeof loadObjective>> | undefined;
  if (krId) {
    const [kr] = await db
      .select()
      .from(keyResults)
      .where(and(eq(keyResults.id, krId), eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)))
      .limit(1);
    if (kr) {
      const obj = await loadObjective(wsId, kr.objectiveId);
      if (obj && obj.scope === "project" && obj.projectId !== input.projectId) {
        result.unlinkedReason = "objective_project_mismatch";
      } else if (obj) {
        objective = obj;
        result.resolvedVia = via;
        result.keyResult = {
          id: kr.id.toString(), title: kr.title,
          baselineValue: kr.baselineValue, targetValue: kr.targetValue, currentValue: kr.currentValue, unit: kr.unit,
        };
        result.objective = { id: obj.id.toString(), title: obj.title, scope: obj.scope as "company" | "project" };
      }
    }
  }

  // Objective công ty: từ objective của KR, hoặc rơi về project.objective_id.
  let companyObj: Awaited<ReturnType<typeof loadObjective>> | undefined;
  if (objective?.scope === "company") {
    companyObj = objective;
  } else {
    const parentId = objective ? (objective.parentObjectiveId ?? project.objectiveId) : project.objectiveId;
    if (parentId) {
      const parent = await loadObjective(wsId, parentId);
      if (parent && parent.scope === "company") {
        companyObj = parent;
        if (result.resolvedVia === "none") result.resolvedVia = "project";
      }
    }
  }

  if (!companyObj) {
    result.unlinkedReason ??=
      project.linkStatus === "intentionally_unlinked" ? "project_intentionally_unlinked" : "project_not_linked";
    return result;
  }

  result.companyObjective = { id: companyObj.id.toString(), title: companyObj.title };
  if (companyObj.goalId) {
    result.goalChain = await loadGoalChain(wsId, companyObj.goalId);
  }
  if (result.goalChain.length === 0) result.unlinkedReason ??= "goal_not_found";
  return result;
}

export function resolveProjectGoalAncestry(wsId: bigint, projectId: bigint): Promise<GoalAncestry> {
  return resolveGoalAncestry(wsId, { projectId, initiativeId: null, keyResultId: null });
}
