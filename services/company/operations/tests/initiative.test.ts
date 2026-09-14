import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  approveInitiative,
  createInitiative,
  getInitiative,
  updateInitiative,
} from "../handlers/initiative.handler";
import { createTask } from "../handlers/task.handler";
import { seedObjectiveWithKeyResult } from "./_helpers";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
    role: "founder",
  });
  // Startup Core: Initiative thuộc một Key Result — seed OKR mặc định.
  const okr = await seedObjectiveWithKeyResult(user.workspaceId, user.projectId);
  return {
    workspaceId: user.workspaceId,
    authorization: `Bearer ${user.accessToken}`,
    objectiveId: okr.objectiveId,
    keyResultId: okr.keyResultId,
  };
}

describe("createInitiative", () => {
  it("creates an initiative with the default active status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Initiative Test Inc");
    const initiative = await createInitiative({ workspaceId, title: "Launch v1", authorization });
    expect(initiative.id).toBeTruthy();
    expect(typeof initiative.id).toBe("string");
    expect(initiative.status).toBe("active");
  });

  it("rejects an initiative for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Initiative Test");
    await expect(createInitiative({ workspaceId: "999999999", title: "Orphan", authorization })).rejects.toThrow();
  });

  it("requires authentication before creating an initiative", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Unauthenticated Initiative Test");

    await expect(
      createInitiative({ workspaceId, title: "Unauthenticated write" })
    ).rejects.toThrow();
  });
});

describe("initiative approval transition", () => {
  it("rejects approvalStatus changes through the general update endpoint", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Protected Initiative Approval");
    const initiative = await createInitiative({
      workspaceId,
      title: "Approval must use governed command",
      authorization,
    });

    await expect(
      updateInitiative({
        id: initiative.id,
        workspaceId,
        authorization,
        approvalStatus: "APPROVED",
      } as any)
    ).rejects.toThrow();
  });
});

describe("getInitiative", () => {
  it("fetches a previously created initiative", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Initiative Inc");
    const created = await createInitiative({ workspaceId, title: "Fetch me", authorization });
    const fetched = await getInitiative({ id: created.id, authorization });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Initiative Inc");
    await expect(getInitiative({ id: "999999999", authorization })).rejects.toThrow();
  });
});

describe("Task.initiativeId FK", () => {
  it("accepts a task linked to a real initiative", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Initiative Link Inc");
    const initiative = await createInitiative({ workspaceId, title: "Linked initiative", authorization });
    await approveInitiative({ id: initiative.id, workspaceId, authorization });
    const task = await createTask({ workspaceId, projectId: workspaceId, title: "Linked task", initiativeId: initiative.id, authorization });
    expect(task.initiativeId).toBe(initiative.id);
  });

  it("rejects a task linked to a non-existent initiative (real DB FK)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Bad Initiative Link Inc");
    await expect(
      createTask({ workspaceId, projectId: workspaceId, title: "Bad link", initiativeId: "999999999", authorization })
    ).rejects.toThrow();
  });
});
