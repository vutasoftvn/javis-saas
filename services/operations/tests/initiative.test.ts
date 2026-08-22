import { describe, expect, it } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createInitiative, getInitiative } from "../handlers/initiative.handler";
import { createTask } from "../handlers/task.handler";

describe("createInitiative", () => {
  it("creates an initiative with the default active status", async () => {
    const workspace = await createWorkspace({ name: "Initiative Test Inc" });
    const initiative = await createInitiative({ workspaceId: workspace.id, title: "Launch v1" });
    expect(initiative.id).toBeGreaterThan(0);
    expect(initiative.status).toBe("active");
  });

  it("rejects an initiative for a workspace that doesn't exist", async () => {
    await expect(createInitiative({ workspaceId: 999999999, title: "Orphan" })).rejects.toThrow();
  });
});

describe("getInitiative", () => {
  it("fetches a previously created initiative", async () => {
    const workspace = await createWorkspace({ name: "Fetch Initiative Inc" });
    const created = await createInitiative({ workspaceId: workspace.id, title: "Fetch me" });
    const fetched = await getInitiative({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getInitiative({ id: 999999999 })).rejects.toThrow();
  });
});

describe("Task.initiativeId FK", () => {
  it("accepts a task linked to a real initiative", async () => {
    const workspace = await createWorkspace({ name: "Task Initiative Link Inc" });
    const initiative = await createInitiative({ workspaceId: workspace.id, title: "Linked initiative" });
    const task = await createTask({ workspaceId: workspace.id, title: "Linked task", initiativeId: initiative.id });
    expect(task.initiativeId).toBe(initiative.id);
  });

  it("rejects a task linked to a non-existent initiative (real DB FK)", async () => {
    const workspace = await createWorkspace({ name: "Bad Initiative Link Inc" });
    await expect(
      createTask({ workspaceId: workspace.id, title: "Bad link", initiativeId: 999999999 })
    ).rejects.toThrow();
  });
});
