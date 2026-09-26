import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createAccount, listAccounts } from "../handlers/account.handler";
import { createContact, listContacts } from "../handlers/contact.handler";
import { createCustomer, listCustomers } from "../handlers/customer.handler";
import {
  createSalesOpportunity,
  listSalesOpportunities,
  updateOpportunityStage,
} from "../handlers/opportunity.handler";

// Đợt 2 (plan 2026-09-26-dashboard-full-management) — API liệt kê cho màn
// CRM. Trước đây frontend gọi `/commercial/workspaces/:id/*` nhưng backend
// chỉ có get-by-id nên danh sách CRM luôn rỗng.

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("CRM list endpoints", () => {
  it("lists accounts, contacts, opportunities and customers of the workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Crm List Inc");
    const account = await createAccount({ workspaceId, name: "Acme", authorization });
    await createContact({ workspaceId, name: "Lan", accountId: account.id, authorization });
    const opp = await createSalesOpportunity({ workspaceId, accountId: account.id, authorization });
    await createCustomer({ workspaceId, accountId: account.id, authorization });

    const { accounts } = await listAccounts({ workspaceId, authorization });
    const { contacts } = await listContacts({ workspaceId, authorization });
    const { opportunities } = await listSalesOpportunities({ workspaceId, authorization });
    const { customers } = await listCustomers({ workspaceId, authorization });

    expect(accounts.map((a) => a.id)).toContain(account.id);
    expect(contacts.map((c) => c.name)).toContain("Lan");
    expect(opportunities.map((o) => o.id)).toContain(opp.id);
    expect(customers.map((c) => c.accountId)).toContain(account.id);
  });

  it("filters contacts by account and opportunities by stage", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Crm Filter Inc");
    const a1 = await createAccount({ workspaceId, name: "A1", authorization });
    const a2 = await createAccount({ workspaceId, name: "A2", authorization });
    await createContact({ workspaceId, name: "Only A1", accountId: a1.id, authorization });
    await createContact({ workspaceId, name: "Only A2", accountId: a2.id, authorization });
    const opp = await createSalesOpportunity({ workspaceId, accountId: a1.id, authorization });
    await updateOpportunityStage({ id: opp.id, stage: "QUALIFIED", workspaceId, authorization });
    await createSalesOpportunity({ workspaceId, accountId: a2.id, authorization });

    const { contacts } = await listContacts({ workspaceId, accountId: a1.id, authorization });
    const { opportunities } = await listSalesOpportunities({ workspaceId, stage: "QUALIFIED", authorization });

    expect(contacts.map((c) => c.name)).toEqual(["Only A1"]);
    expect(opportunities.map((o) => o.id)).toEqual([opp.id]);
  });

  it("does not leak another workspace's records and rejects outsiders", async () => {
    const owner = await makeAuthedWorkspace("Crm Owner Inc");
    const other = await makeAuthedWorkspace("Crm Other Inc");
    await createAccount({ workspaceId: owner.workspaceId, name: "Private", authorization: owner.authorization });

    const { accounts } = await listAccounts({ workspaceId: other.workspaceId, authorization: other.authorization });
    expect(accounts.map((a) => a.name)).not.toContain("Private");

    await expect(
      listAccounts({ workspaceId: owner.workspaceId, authorization: other.authorization })
    ).rejects.toThrow();
  });
});
