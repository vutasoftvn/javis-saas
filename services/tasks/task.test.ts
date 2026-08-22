import { describe, expect, it } from "vitest";
import { createTask, getTask } from "./task";

describe("createTask", () => {
  it("creates a task with default priority and open status", async () => {
    const task = await createTask({ workspaceId: "ws1", title: "Write plan" });
    expect(task.id).toBeGreaterThan(0);
    expect(task.workspaceId).toBe("ws1");
    expect(task.title).toBe("Write plan");
    expect(task.status).toBe("open");
    expect(task.priority).toBe("medium");
  });

  it("accepts an explicit priority", async () => {
    const task = await createTask({ workspaceId: "ws1", title: "Urgent", priority: "high" });
    expect(task.priority).toBe("high");
  });
});

describe("getTask", () => {
  it("returns a previously created task", async () => {
    const created = await createTask({ workspaceId: "ws1", title: "Fetch me" });
    const fetched = await getTask({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getTask({ id: 999999999 })).rejects.toThrow();
  });
});
