import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createAccount, getAccount } from "../handlers/account.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createAccount", () => {
  it("creates an account with the default TARGET lifecycle status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Account Test Inc");
    const account = await createAccount({ workspaceId, name: "Acme Corp", authorization });
    expect(account.id).toBeDefined();
    expect(account.lifecycleStatus).toBe("TARGET");
  });

  it("rejects an account for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Account Test");
    await expect(
      createAccount({ workspaceId: "999999999", name: "Orphan Corp", authorization })
    ).rejects.toThrow();
  });

  it("rejects a duplicate domain within the same workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Dup Domain Inc");
    await createAccount({ workspaceId, name: "First", domain: "acme.com", authorization });
    await expect(
      createAccount({ workspaceId, name: "Second", domain: "acme.com", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Account Ws");
    const outsider = await makeAuthedWorkspace("Outsider Account Test");
    await expect(
      createAccount({ workspaceId, name: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getAccount", () => {
  it("fetches a previously created account", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Account Inc");
    const created = await createAccount({ workspaceId, name: "Fetch me", authorization });
    const fetched = await getAccount({ id: created.id, authorization });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Account Test");
    await expect(getAccount({ id: "999999999", authorization })).rejects.toThrow();
  });
});
