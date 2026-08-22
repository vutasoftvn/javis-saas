import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount, getAccount } from "./account";

describe("createAccount", () => {
  it("creates an account with the default TARGET lifecycle status", async () => {
    const workspace = await createWorkspace({ name: "Account Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    expect(account.id).toBeGreaterThan(0);
    expect(account.lifecycleStatus).toBe("TARGET");
  });

  it("rejects an account for a workspace that doesn't exist", async () => {
    await expect(createAccount({ workspaceId: 999999999, name: "Orphan Corp" })).rejects.toThrow();
  });

  it("rejects a duplicate domain within the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Domain Inc" });
    await createAccount({ workspaceId: workspace.id, name: "First", domain: "acme.com" });
    await expect(
      createAccount({ workspaceId: workspace.id, name: "Second", domain: "acme.com" })
    ).rejects.toThrow();
  });
});

describe("getAccount", () => {
  it("fetches a previously created account", async () => {
    const workspace = await createWorkspace({ name: "Fetch Account Inc" });
    const created = await createAccount({ workspaceId: workspace.id, name: "Fetch me" });
    const fetched = await getAccount({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getAccount({ id: 999999999 })).rejects.toThrow();
  });
});
