import { describe, expect, it } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createChecklistItem, getChecklistItem, completeChecklistItem } from "../handlers/legal-checklist-item.handler";

describe("createChecklistItem", () => {
  it("creates a checklist item with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Checklist Test Inc" });
    const item = await createChecklistItem({ workspaceId: workspace.id, title: "Register business license" });
    expect(item.id).toBeGreaterThan(0);
    expect(item.status).toBe("OPEN");
  });

  it("rejects an item for a workspace that doesn't exist", async () => {
    await expect(
      createChecklistItem({ workspaceId: 999999999, title: "Orphan item" })
    ).rejects.toThrow();
  });
});

describe("getChecklistItem/completeChecklistItem", () => {
  it("fetches an item and marks it done", async () => {
    const workspace = await createWorkspace({ name: "Complete Checklist Inc" });
    const created = await createChecklistItem({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getChecklistItem({ id: created.id });
    expect(fetched).toEqual(created);

    const done = await completeChecklistItem({ id: created.id });
    expect(done.status).toBe("DONE");
  });

  it("throws not found for a missing id", async () => {
    await expect(getChecklistItem({ id: 999999999 })).rejects.toThrow();
  });
});
