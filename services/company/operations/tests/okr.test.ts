import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createOkrCycle, createObjective, addKeyResult, checkin, getObjectiveProgress, getObjective, linkObjectiveProjects_Endpoint, getObjectiveProjects, unlinkObjectiveProject_Endpoint } from "../handlers/okr.handler";
import { createProject } from "../handlers/project.handler";

async function makeCycle() {
  const workspace = await createWorkspace({ name: `OKR Test ${Date.now()}` });
  const cycle = await createOkrCycle({ workspaceId: workspace.id, name: "Q1" });
  return { workspace, cycle };
}

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, userId: user.userId, authorization: `Bearer ${user.accessToken}` };
}

describe("createOkrCycle", () => {
  it("creates a cycle with the default draft status", async () => {
    const { cycle } = await makeCycle();
    expect(cycle.id).toBeTruthy();
    expect(typeof cycle.id).toBe("string");
    expect(cycle.status).toBe("draft");
  });

  it("rejects a cycle for a workspace that doesn't exist", async () => {
    await expect(createOkrCycle({ workspaceId: "999999999", name: "Bad" })).rejects.toThrow();
  });
});

describe("createObjective", () => {
  it("creates an objective under a cycle", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    expect(objective.id).toBeTruthy();
    expect(typeof objective.id).toBe("string");
    expect(objective.cycleId).toBe(cycle.id);
  });

  it("rejects an objective under a cycle that doesn't exist (real DB FK)", async () => {
    const { workspace } = await makeCycle();
    await expect(
      createObjective({ workspaceId: workspace.id, cycleId: "999999999", title: "Orphan" })
    ).rejects.toThrow();
  });
});

describe("addKeyResult + checkin + getObjectiveProgress", () => {
  it("scores an objective from its key results after check-ins", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    const kr1 = await addKeyResult({ objectiveId: objective.id, title: "Sign 10 customers", targetValue: 10 });
    const kr2 = await addKeyResult({ objectiveId: objective.id, title: "Reach $10k MRR", targetValue: 10000 });

    await checkin({ id: kr1.id, value: 5 });
    await checkin({ id: kr2.id, value: 10000 });

    const progress = await getObjectiveProgress({ objectiveId: objective.id });
    expect(progress.score).toBeCloseTo(0.75);
    expect(progress.keyResults).toHaveLength(2);
  });
});

describe("linkObjectiveProjects / getObjectiveProjects / unlinkObjectiveProject", () => {
  it("links an objective to multiple projects and returns stable IDs", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Objective Link Test Inc");

    // Create cycle in first workspace
    const cycle = await createOkrCycle({ workspaceId, name: "Q1" });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Multi-project objective" });

    const project1 = await createProject({ workspaceId, title: "Project O1", authorization });
    const project2 = await createProject({ workspaceId, title: "Project O2", authorization });

    const response = await linkObjectiveProjects_Endpoint({
      id: objective.id,
      workspaceId,
      authorization,
      projectIds: [project1.id, project2.id],
    });

    expect(response.projectIds).toHaveLength(2);
    expect(response.projectIds).toContain(project1.id);
    expect(response.projectIds).toContain(project2.id);
  });

  it("returns empty projectIds when no links exist", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Objective No Links Test");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1" });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Unlinked objective" });

    const response = await getObjectiveProjects({
      id: objective.id,
      workspaceId,
      authorization,
    });

    expect(response.projectIds).toEqual([]);
  });

  it("makes duplicate add idempotent", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Objective Idempotent Link Test");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1" });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Idempotent link objective" });
    const project = await createProject({ workspaceId, title: "Project Y", authorization });

    // First link
    await linkObjectiveProjects_Endpoint({
      id: objective.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    // Second link (should be idempotent)
    const response = await linkObjectiveProjects_Endpoint({
      id: objective.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    expect(response.projectIds).toHaveLength(1);
    expect(response.projectIds[0]).toBe(project.id);
  });

  it("unlinks a project and leaves others intact", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Objective Unlink Test");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1" });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Multi-link objective" });
    const project1 = await createProject({ workspaceId, title: "Project 3", authorization });
    const project2 = await createProject({ workspaceId, title: "Project 4", authorization });

    // Link both
    await linkObjectiveProjects_Endpoint({
      id: objective.id,
      workspaceId,
      authorization,
      projectIds: [project1.id, project2.id],
    });

    // Unlink one
    await unlinkObjectiveProject_Endpoint({
      id: objective.id,
      projectId: project1.id,
      workspaceId,
      authorization,
    });

    // Verify only one remains
    const response = await getObjectiveProjects({
      id: objective.id,
      workspaceId,
      authorization,
    });

    expect(response.projectIds).toHaveLength(1);
    expect(response.projectIds[0]).toBe(project2.id);
  });

  it("rejects link to a project in another workspace without disclosing it", async () => {
    const workspace1 = await makeAuthedWorkspace("Objective Link W1");
    const workspace2 = await makeAuthedWorkspace("Objective Link W2");

    const cycle = await createOkrCycle({ workspaceId: workspace1.workspaceId, name: "Q1" });
    const objective = await createObjective({
      workspaceId: workspace1.workspaceId,
      cycleId: cycle.id,
      title: "Objective in W1",
    });

    const projectInW2 = await createProject({
      workspaceId: workspace2.workspaceId,
      title: "Project in W2",
      authorization: workspace2.authorization,
    });

    // Try to link objective in W1 to project in W2 — should fail
    await expect(
      linkObjectiveProjects_Endpoint({
        id: objective.id,
        workspaceId: workspace1.workspaceId,
        authorization: workspace1.authorization,
        projectIds: [projectInW2.id],
      })
    ).rejects.toThrow("not found");
  });
});

describe("getObjective", () => {
  it("member fetches their objective and projectIds are populated", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Get Objective Test");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1" });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Objective with projects" });
    const project = await createProject({ workspaceId, title: "Linked Project", authorization });

    // Link project to objective
    await linkObjectiveProjects_Endpoint({
      id: objective.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    // Fetch objective and verify projectIds are populated
    const fetched = await getObjective({ id: objective.id, authorization });
    expect(fetched.id).toBe(objective.id);
    expect(fetched.projectIds).toHaveLength(1);
    expect(fetched.projectIds[0]).toBe(project.id);
  });

  it("non-member is rejected when fetching an objective from another workspace", async () => {
    const workspace1 = await makeAuthedWorkspace("Get Objective W1");
    const workspace2 = await makeAuthedWorkspace("Get Objective W2");

    const cycle = await createOkrCycle({ workspaceId: workspace1.workspaceId, name: "Q1" });
    const objective = await createObjective({
      workspaceId: workspace1.workspaceId,
      cycleId: cycle.id,
      title: "Private Objective",
    });

    // Try to fetch objective from W1 using W2 member credentials
    await expect(getObjective({ id: objective.id, authorization: workspace2.authorization })).rejects.toThrow();
  });
});
