import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createAccount } from "../handlers/account.handler";
import { createContact, getContact } from "../handlers/contact.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createContact", () => {
  it("creates a contact linked to an account", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Contact Test Inc");
    const account = await createAccount({ workspaceId, name: "Acme Corp", authorization });
    const contact = await createContact({ workspaceId, accountId: account.id, name: "Jane Doe", authorization });
    expect(contact.id).toBeDefined();
    expect(contact.accountId).toBe(account.id);
    expect(contact.doNotContact).toBe(false);
  });

  it("creates a contact with no account (unassociated lead contact)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("No Account Contact Inc");
    const contact = await createContact({ workspaceId, name: "Cold Contact", authorization });
    expect(contact.accountId).toBeNull();
  });

  it("rejects a duplicate email within the same workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Dup Email Inc");
    await createContact({ workspaceId, name: "First", email: "same@example.com", authorization });
    await expect(
      createContact({ workspaceId, name: "Second", email: "same@example.com", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Contact Ws");
    const outsider = await makeAuthedWorkspace("Outsider Contact Test");
    await expect(
      createContact({ workspaceId, name: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getContact", () => {
  it("fetches a previously created contact", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Contact Inc");
    const created = await createContact({ workspaceId, name: "Fetch me", authorization });
    const fetched = await getContact({ id: created.id, authorization });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Contact Test");
    await expect(getContact({ id: "999999999", authorization })).rejects.toThrow();
  });
});
