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
});
