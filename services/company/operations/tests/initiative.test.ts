import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createInitiative, getInitiative } from "../handlers/initiative.handler";
import { createTask } from "../handlers/task.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
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
    await expect(createInitiative({ workspaceId: 999999999, title: "Orphan", authorization })).rejects.toThrow();
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
    await expect(getInitiative({ id: 999999999, authorization })).rejects.toThrow();
  });
});

describe("Task.initiativeId FK", () => {
  it("accepts a task linked to a real initiative", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Initiative Link Inc");
    const initiative = await createInitiative({ workspaceId, title: "Linked initiative", authorization });
    const task = await createTask({ workspaceId, title: "Linked task", initiativeId: initiative.id, authorization });
    expect(task.initiativeId).toBe(initiative.id);
  });

  it("rejects a task linked to a non-existent initiative (real DB FK)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Bad Initiative Link Inc");
    await expect(
      createTask({ workspaceId, title: "Bad link", initiativeId: 999999999, authorization })
    ).rejects.toThrow();
  });
});

