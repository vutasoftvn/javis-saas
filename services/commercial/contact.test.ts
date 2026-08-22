import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createContact, getContact } from "./contact";

describe("createContact", () => {
  it("creates a contact linked to an account", async () => {
    const workspace = await createWorkspace({ name: "Contact Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const contact = await createContact({ workspaceId: workspace.id, accountId: account.id, name: "Jane Doe" });
    expect(contact.id).toBeGreaterThan(0);
    expect(contact.accountId).toBe(account.id);
    expect(contact.doNotContact).toBe(false);
  });

  it("creates a contact with no account (unassociated lead contact)", async () => {
    const workspace = await createWorkspace({ name: "No Account Contact Inc" });
    const contact = await createContact({ workspaceId: workspace.id, name: "Cold Contact" });
    expect(contact.accountId).toBeNull();
  });

  it("rejects a duplicate email within the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Email Inc" });
    await createContact({ workspaceId: workspace.id, name: "First", email: "same@example.com" });
    await expect(
      createContact({ workspaceId: workspace.id, name: "Second", email: "same@example.com" })
    ).rejects.toThrow();
  });
});

describe("getContact", () => {
  it("fetches a previously created contact", async () => {
    const workspace = await createWorkspace({ name: "Fetch Contact Inc" });
    const created = await createContact({ workspaceId: workspace.id, name: "Fetch me" });
    const fetched = await getContact({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getContact({ id: 999999999 })).rejects.toThrow();
  });
});
