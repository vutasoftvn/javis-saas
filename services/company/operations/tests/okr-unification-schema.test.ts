import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";

async function seed() {
  const user = await createTestSession({
    email: `okr-schema-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "OKR Schema",
    role: "founder",
  });
  const ws = BigInt(user.workspaceId);
  const goalId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.goals (id, workspace_id, title, goal_type)
    VALUES (${goalId}, ${ws}, 'G', 'strategic')`);
  return { ws, projectId: BigInt(user.projectId), goalId };
}

async function dbError(p: Promise<unknown>): Promise<string> {
  try {
    await p;
  } catch (e) {
    const err = e as { message?: string; cause?: { message?: string } };
    return `${err.message ?? ""} ${err.cause?.message ?? ""}`;
  }
  return "";
}

describe("okr_objectives unification constraints (038)", () => {
  it("legacy-style insert (project_id only) defaults to scope=project", async () => {
    const { ws, projectId } = await seed();
    const id = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title)
      VALUES (${id}, ${ws}, ${projectId}, 'legacy')`);
    const rows = await db.execute(sql`SELECT scope FROM strategy.okr_objectives WHERE id = ${id}`);
    expect((rows.rows ?? rows)[0].scope).toBe("project");
  });

  it("rejects a company objective without goal_id", async () => {
    const { ws } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, title)
      VALUES (${generateSnowflake()}, ${ws}, 'company', 'no goal')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("rejects a company objective that has a project_id", async () => {
    const { ws, projectId, goalId } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, project_id, title)
      VALUES (${generateSnowflake()}, ${ws}, 'company', ${goalId}, ${projectId}, 'bad')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("rejects a project objective without project_id", async () => {
    const { ws } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, title)
      VALUES (${generateSnowflake()}, ${ws}, 'project', 'orphan')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("accepts company objective then project objective aligned to it", async () => {
    const { ws, projectId, goalId } = await seed();
    const companyId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, title)
      VALUES (${companyId}, ${ws}, 'company', ${goalId}, 'Company O')`);
    const projId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, project_id, parent_objective_id, title)
      VALUES (${projId}, ${ws}, 'project', ${projectId}, ${companyId}, 'Project O')`);
    const rows = await db.execute(sql`SELECT parent_objective_id FROM strategy.okr_objectives WHERE id = ${projId}`);
    expect(String((rows.rows ?? rows)[0].parent_objective_id)).toBe(companyId.toString());
  });

  it("rejects a parent that is itself a project objective", async () => {
    const { ws, projectId } = await seed();
    const a = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title)
      VALUES (${a}, ${ws}, ${projectId}, 'A')`);
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, parent_objective_id, title)
      VALUES (${generateSnowflake()}, ${ws}, ${projectId}, ${a}, 'B')`));
    expect(msg).toMatch(/company-scope objective/);
  });

  it("rejects a goal from another workspace (composite FK)", async () => {
    const mine = await seed();
    const other = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, title)
      VALUES (${generateSnowflake()}, ${mine.ws}, 'company', ${other.goalId}, 'cross-tenant')`));
    expect(msg).toMatch(/fk_okr_objective_goal_ws/);
  });
});
