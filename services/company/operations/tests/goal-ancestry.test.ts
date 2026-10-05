// services/company/operations/tests/goal-ancestry.test.ts
import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createGoalService } from "../services/goals.service";
import { createObjectiveService, addKeyResultService } from "../services/okr.service";
import { resolveGoalAncestry, resolveGoalAncestrySafe, resolveProjectGoalAncestry } from "../services/goal-ancestry.service";

async function world() {
  const user = await createTestSession({
    email: `ancestry-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Ancestry", role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ws = BigInt(user.workspaceId);
  const project = BigInt(user.projectId);
  const parent = await createGoalService({ workspaceId: user.workspaceId, title: "Vision", goalType: "vision" });
  const goal = await createGoalService({
    workspaceId: user.workspaceId, parentId: parent.goalId, title: "Chiến lược Q4", goalType: "strategic",
  });
  const company = await createObjectiveService({
    workspaceId: user.workspaceId, scope: "company", goalId: goal.goalId, title: "Tăng trưởng", authorization,
  });
  const projObj = await createObjectiveService({
    workspaceId: user.workspaceId, projectId: user.projectId, parentObjectiveId: company.id, title: "MRR dự án", authorization,
  });
  const kr = await addKeyResultService({
    objectiveId: projObj.id, title: "MRR", targetValue: 100, baselineValue: 10, unit: "triệu", authorization,
  });
  const initiativeId = generateSnowflake();
  await db.insert(schema.initiatives).values({
    id: initiativeId, workspaceId: ws, projectId: project, keyResultId: BigInt(kr.id), title: "Chiến dịch",
  });
  return { user, ws, project, goal, parent, company, projObj, kr, initiativeId, authorization };
}

describe("resolveGoalAncestry", () => {
  it("walks initiative -> KR -> project objective -> company objective -> goal chain", async () => {
    const w = await world();
    const a = await resolveGoalAncestry(w.ws, { projectId: w.project, initiativeId: w.initiativeId, keyResultId: null });
    expect(a.resolvedVia).toBe("initiative");
    expect(a.keyResult).toMatchObject({ id: w.kr.id, targetValue: 100, baselineValue: 10, unit: "triệu" });
    expect(a.objective).toMatchObject({ id: w.projObj.id, scope: "project" });
    expect(a.companyObjective).toMatchObject({ id: w.company.id, title: "Tăng trưởng" });
    expect(a.goalChain.map((g) => g.title)).toEqual(["Chiến lược Q4", "Vision"]);
    expect(a.unlinkedReason).toBeNull();
  });

  it("uses key_result directly when there is no initiative", async () => {
    const w = await world();
    const a = await resolveGoalAncestry(w.ws, { projectId: w.project, initiativeId: null, keyResultId: BigInt(w.kr.id) });
    expect(a.resolvedVia).toBe("key_result");
    expect(a.goalChain[0]?.title).toBe("Chiến lược Q4");
  });

  it("falls back to projects.objective_id when the task has no initiative or KR", async () => {
    const w = await world();
    await db.update(schema.projects).set({ objectiveId: BigInt(w.company.id) }).where(eq(schema.projects.id, w.project));
    const a = await resolveProjectGoalAncestry(w.ws, w.project);
    expect(a.resolvedVia).toBe("project");
    expect(a.keyResult).toBeNull();
    expect(a.companyObjective?.id).toBe(w.company.id);
    expect(a.goalChain.map((g) => g.title)).toEqual(["Chiến lược Q4", "Vision"]);
  });

  it("reports project_not_linked when nothing links the project to a company objective", async () => {
    const w = await world();
    await db.update(schema.projects).set({ objectiveId: null }).where(eq(schema.projects.id, w.project));
    const a = await resolveProjectGoalAncestry(w.ws, w.project);
    expect(a.goalChain).toEqual([]);
    expect(a.unlinkedReason).toBe("project_not_linked");
  });

  it("ignores a project-scope objective that belongs to a different project", async () => {
    const w = await world();
    const otherProject = generateSnowflake();
    await db.insert(schema.projects).values({
      id: otherProject, workspaceId: w.ws, title: "Dự án khác", status: "ACTIVE", lifecycleStage: "P0_DISCOVERY",
    });
    const a = await resolveGoalAncestry(w.ws, { projectId: otherProject, initiativeId: null, keyResultId: BigInt(w.kr.id) });
    expect(a.unlinkedReason).toBe("objective_project_mismatch");
    expect(a.keyResult).toBeNull();
  });

  it("does not leak another workspace's data", async () => {
    const w = await world();
    const other = await world();
    const a = await resolveGoalAncestry(other.ws, { projectId: w.project, initiativeId: w.initiativeId, keyResultId: null });
    expect(a.resolvedVia).toBe("none");
    expect(a.unlinkedReason).toBe("project_not_found");
  });
});

describe("resolveGoalAncestry extra cases", () => {
  it("stops the goal chain at the workspace boundary when parent_id points to another workspace", async () => {
    const w = await world();
    const other = await world();
    await db.update(schema.goals)
      .set({ parentId: BigInt(other.parent.goalId) })
      .where(eq(schema.goals.id, BigInt(w.goal.goalId)));
    const a = await resolveGoalAncestry(w.ws, { projectId: w.project, initiativeId: w.initiativeId, keyResultId: null });
    expect(a.goalChain.map((g) => g.title)).toEqual(["Chiến lược Q4"]);
    expect(a.goalChain.some((g) => g.title === "Vision")).toBe(false);
  });

  it("truncates a goal chain deeper than 8 levels to 8", async () => {
    const w = await world();
    let parentId: string | undefined;
    let leaf = "";
    for (let i = 0; i < 10; i++) {
      const g = await createGoalService({
        workspaceId: w.user.workspaceId, parentId, title: `Deep ${i}`, goalType: "tactical",
      });
      parentId = g.goalId;
      leaf = g.goalId;
    }
    await db.update(schema.okrObjectives).set({ goalId: BigInt(leaf) }).where(eq(schema.okrObjectives.id, BigInt(w.company.id)));
    await db.update(schema.projects).set({ objectiveId: BigInt(w.company.id) }).where(eq(schema.projects.id, w.project));
    const a = await resolveProjectGoalAncestry(w.ws, w.project);
    expect(a.goalChain).toHaveLength(8);
    expect(a.goalChain[0]?.title).toBe("Deep 9");
    expect(a.unlinkedReason).toBeNull();
  });

  it("reports project_intentionally_unlinked", async () => {
    const w = await world();
    await db.update(schema.projects)
      .set({ objectiveId: null, linkStatus: "intentionally_unlinked" })
      .where(eq(schema.projects.id, w.project));
    const a = await resolveProjectGoalAncestry(w.ws, w.project);
    expect(a.unlinkedReason).toBe("project_intentionally_unlinked");
    expect(a.goalChain).toEqual([]);
  });
});

describe("resolveGoalAncestrySafe", () => {
  it("degrades to an empty ancestry when the resolver throws", async () => {
    const input = { projectId: 1n, initiativeId: null, keyResultId: null };
    const errors: unknown[] = [];
    const boom = async () => { throw new Error("db down"); };
    const a = await resolveGoalAncestrySafe(1n, input, boom, (e) => errors.push(e));
    const b = await resolveGoalAncestrySafe(1n, input, boom);
    expect(a).toEqual({
      resolvedVia: "none", project: null, keyResult: null, objective: null,
      companyObjective: null, goalChain: [], unlinkedReason: "resolve_failed",
    });
    expect(errors).toHaveLength(1);
    expect(a).not.toBe(b);
    expect(a.goalChain).not.toBe(b.goalChain);
  });

  it("still returns the empty ancestry when onError itself throws", async () => {
    const input = { projectId: 1n, initiativeId: null, keyResultId: null };
    const a = await resolveGoalAncestrySafe(
      1n, input, async () => { throw new Error("db down"); }, () => { throw new Error("logger down"); },
    );
    expect(a.unlinkedReason).toBe("resolve_failed");
    expect(a.goalChain).toEqual([]);
  });

  it("matches resolveGoalAncestry with the real resolver", async () => {
    const w = await world();
    const input = { projectId: w.project, initiativeId: w.initiativeId, keyResultId: null };
    expect(await resolveGoalAncestrySafe(w.ws, input)).toEqual(await resolveGoalAncestry(w.ws, input));
  });
});
