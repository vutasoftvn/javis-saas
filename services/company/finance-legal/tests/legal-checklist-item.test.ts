import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createChecklistItem, getChecklistItem, completeChecklistItem } from "../handlers/legal-checklist-item.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createChecklistItem", () => {
  it("creates a checklist item with the default OPEN status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Checklist Test Inc");
    const item = await createChecklistItem({ workspaceId, title: "Register business license", authorization });
    expect(item.id).toBeTruthy();
    expect(item.status).toBe("OPEN");
  });

  it("rejects an item for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Checklist Test");
    await expect(
      createChecklistItem({ workspaceId: 999999999, title: "Orphan item", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Checklist Ws");
    const outsider = await makeAuthedWorkspace("Outsider Checklist Test");
    await expect(
      createChecklistItem({ workspaceId, title: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getChecklistItem/completeChecklistItem", () => {
  it("fetches an item and marks it done", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Complete Checklist Inc");
    const created = await createChecklistItem({ workspaceId, title: "Fetch me", authorization });

    const fetched = await getChecklistItem({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const done = await completeChecklistItem({ id: created.id, authorization });
    expect(done.status).toBe("DONE");
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Checklist Test");
    await expect(getChecklistItem({ id: 999999999, authorization })).rejects.toThrow();
  });
});
