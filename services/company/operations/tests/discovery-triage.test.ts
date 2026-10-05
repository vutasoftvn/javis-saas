import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createGoalService } from "../services/goals.service";
import { createObjectiveService } from "../services/okr.service";
import { triageProjectService } from "../services/discovery-project.service";

async function setup() {
  const user = await createTestSession({
    email: `triage-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Triage",
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const { goalId } = await createGoalService({ workspaceId: user.workspaceId, title: "G", goalType: "strategic" });
  const company = await createObjectiveService({
    workspaceId: user.workspaceId, scope: "company", goalId, title: "C", authorization,
  });
  return { user, authorization, goalId, company };
}

async function projectObjectiveId(projectId: string) {
  const r = await db.execute(sql`SELECT objective_id, link_status FROM strategy.projects WHERE id = ${BigInt(projectId)}`);
  return (r.rows ?? r)[0] as { objective_id: string | null; link_status: string };
}

describe("project triage on unified OKR", () => {
  it("link attaches a project to a company objective", async () => {
    const { user, company } = await setup();
    await triageProjectService({
      workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: company.id,
    });
    const row = await projectObjectiveId(user.projectId);
    expect(String(row.objective_id)).toBe(company.id);
    expect(row.link_status).toBe("linked");
  });

  it("link rejects a project-scope objective", async () => {
    const { user, authorization } = await setup();
    const projObj = await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "P", authorization,
    });
    await expect(
      triageProjectService({
        workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: projObj.id,
      }),
    ).rejects.toThrow(/company/);
  });

  it("link rejects when the project already has an objective aligned to a different parent", async () => {
    const { user, authorization, goalId, company } = await setup();
    const other = await createObjectiveService({
      workspaceId: user.workspaceId, scope: "company", goalId, title: "Other", authorization,
    });
    await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, parentObjectiveId: other.id, title: "P", authorization,
    });
    await expect(
      triageProjectService({
        workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: company.id,
      }),
    ).rejects.toThrow(/parent/);
  });

  it("roll_to_new_goal creates a company objective under the new goal and links the project", async () => {
    const { user } = await setup();
    const { goalId: newGoal } = await createGoalService({
      workspaceId: user.workspaceId, title: "Next", goalType: "tactical",
    });
    await triageProjectService({
      workspaceId: user.workspaceId, projectId: user.projectId, action: "roll_to_new_goal",
      newGoalId: newGoal, newObjectiveTitle: "Rolled",
    });
    const row = await projectObjectiveId(user.projectId);
    expect(row.objective_id).not.toBeNull();
    expect(row.link_status).toBe("linked");
    const o = (await db.execute(sql`SELECT scope, goal_id, workspace_id FROM strategy.okr_objectives WHERE id = ${BigInt(row.objective_id as string)}`));
    const obj = (o.rows ?? o)[0] as { scope: string; goal_id: string; workspace_id: string };
    expect(obj.scope).toBe("company");
    expect(String(obj.goal_id)).toBe(newGoal);
    expect(String(obj.workspace_id)).toBe(user.workspaceId);
  });

  it("roll_to_new_goal rejects a project with objectives aligned elsewhere and creates no orphan", async () => {
    const { user, authorization, goalId, company } = await setup();
    await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, parentObjectiveId: company.id, title: "P", authorization,
    });
    const { goalId: newGoal } = await createGoalService({
      workspaceId: user.workspaceId, title: "Next", goalType: "tactical",
    });
    const count = async () => {
      const r = await db.execute(sql`SELECT count(*)::int AS n FROM strategy.okr_objectives WHERE workspace_id = ${BigInt(user.workspaceId)} AND scope = 'company'`);
      return Number(((r.rows ?? r)[0] as { n: number }).n);
    };
    const before = await count();
    expect(goalId).toBeTruthy();
    await expect(
      triageProjectService({
        workspaceId: user.workspaceId, projectId: user.projectId, action: "roll_to_new_goal",
        newGoalId: newGoal, newObjectiveTitle: "Rolled",
      }),
    ).rejects.toThrow(/parent/);
    expect(await count()).toBe(before);
    expect((await projectObjectiveId(user.projectId)).objective_id).toBeNull();
  });

  it("cross-workspace targetObjectiveId and newGoalId are not found", async () => {
    const a = await setup();
    const b = await setup();
    await expect(
      triageProjectService({
        workspaceId: a.user.workspaceId, projectId: a.user.projectId, action: "link", targetObjectiveId: b.company.id,
      }),
    ).rejects.toMatchObject({ code: "not_found" });
    await expect(
      triageProjectService({
        workspaceId: a.user.workspaceId, projectId: a.user.projectId, action: "roll_to_new_goal",
        newGoalId: b.goalId, newObjectiveTitle: "X",
      }),
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("DB trigger blocks pointing projects.objective_id at a project-scope objective", async () => {
    const { user, authorization } = await setup();
    const projObj = await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "P", authorization,
    });
    let message = "";
    try {
      await db.execute(sql`UPDATE strategy.projects SET objective_id = ${BigInt(projObj.id)} WHERE id = ${BigInt(user.projectId)}`);
    } catch (e) {
      const err = e as { message?: string; cause?: { message?: string } };
      message = `${err.message ?? ""} ${err.cause?.message ?? ""}`;
    }
    expect(message).toMatch(/company-scope objective/);
  });

  it("createObjective with a parent different from the project's objective is failedPrecondition", async () => {
    const { user, authorization, goalId, company } = await setup();
    const other = await createObjectiveService({
      workspaceId: user.workspaceId, scope: "company", goalId, title: "Other", authorization,
    });
    await triageProjectService({
      workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: company.id,
    });
    await expect(
      createObjectiveService({
        workspaceId: user.workspaceId, projectId: user.projectId, parentObjectiveId: other.id, title: "P", authorization,
      }),
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });
});
