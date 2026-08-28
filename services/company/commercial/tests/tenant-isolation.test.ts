import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { createAccount, getAccount } from "../handlers/account.handler";
import { createContact, getContact } from "../handlers/contact.handler";
import { createCustomer, getCustomer } from "../handlers/customer.handler";
import { createSalesLead, getSalesLead, updateLeadStage } from "../handlers/lead.handler";
import { createSalesOpportunity, getSalesOpportunity, updateOpportunityStage } from "../handlers/opportunity.handler";
import { getAccountService } from "../services/account.service";
import { getContactService } from "../services/contact.service";
import { getCustomerService } from "../services/customer.service";
import { getSalesLeadService, updateLeadStageService } from "../services/lead.service";
import { getSalesOpportunityService, updateOpportunityStageService } from "../services/opportunity.service";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx, user };
}

describe("Commercial Tenant Isolation & Query Scope", () => {
  it("Account: cross-workspace lookup returns 404 at query layer", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Acct A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Acct B");

    const acctB = await createAccount({
      workspaceId: wsB.workspaceId,
      name: "Acme Tenant B",
      authorization: wsB.authorization,
    });

    // Service level: ctxA lookup acctB must throw 404
    await expect(getAccountService(acctB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    // Service level: ctxB lookup acctB must succeed
    const fetchedByB = await getAccountService(acctB.id, wsB.ctx);
    expect(fetchedByB.id).toBe(acctB.id);

    // Handler level: wsA caller requesting acctB in wsA scope must throw 404
    await expect(
      getAccount({ id: acctB.id, workspaceId: wsA.workspaceId, authorization: wsA.authorization })
    ).rejects.toThrow(/not found/i);
  });

  it("Contact: cross-workspace lookup returns 404 at query layer", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Contact A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Contact B");

    const contactB = await createContact({
      workspaceId: wsB.workspaceId,
      name: "Contact B",
      authorization: wsB.authorization,
    });

    await expect(getContactService(contactB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    const fetchedByB = await getContactService(contactB.id, wsB.ctx);
    expect(fetchedByB.id).toBe(contactB.id);

    await expect(
      getContact({ id: contactB.id, workspaceId: wsA.workspaceId, authorization: wsA.authorization })
    ).rejects.toThrow(/not found/i);
  });

  it("Customer: cross-workspace lookup returns 404 at query layer", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Customer A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Customer B");

    const acctB = await createAccount({
      workspaceId: wsB.workspaceId,
      name: "Customer Parent B",
      authorization: wsB.authorization,
    });
    const customerB = await createCustomer({
      workspaceId: wsB.workspaceId,
      accountId: acctB.id,
      authorization: wsB.authorization,
    });

    await expect(getCustomerService(customerB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    const fetchedByB = await getCustomerService(customerB.id, wsB.ctx);
    expect(fetchedByB.id).toBe(customerB.id);

    await expect(
      getCustomer({ id: customerB.id, workspaceId: wsA.workspaceId, authorization: wsA.authorization })
    ).rejects.toThrow(/not found/i);
  });

  it("Lead: cross-workspace get & update returns 404 and leaves record unchanged", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Lead A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Lead B");

    const leadB = await createSalesLead({
      workspaceId: wsB.workspaceId,
      name: "Lead in Workspace B",
      authorization: wsB.authorization,
    });
    expect(leadB.stage).toBe("NEW");

    // wsA get fails
    await expect(getSalesLeadService(leadB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    // wsA update fails
    await expect(updateLeadStageService(leadB.id, "QUALIFIED", wsA.ctx)).rejects.toThrow(/not found/i);
    await expect(
      updateLeadStage({
        id: leadB.id,
        stage: "QUALIFIED",
        workspaceId: wsA.workspaceId,
        authorization: wsA.authorization,
      })
    ).rejects.toThrow(/not found/i);

    // Verify record B was not mutated
    const stillNew = await getSalesLeadService(leadB.id, wsB.ctx);
    expect(stillNew.stage).toBe("NEW");
  });

  it("Opportunity: cross-workspace get & update returns 404 and leaves record unchanged", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Opp A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Opp B");

    const acctB = await createAccount({
      workspaceId: wsB.workspaceId,
      name: "Opp Parent B",
      authorization: wsB.authorization,
    });
    const oppB = await createSalesOpportunity({
      workspaceId: wsB.workspaceId,
      accountId: acctB.id,
      authorization: wsB.authorization,
    });
    expect(oppB.stage).toBe("DISCOVERY");

    // wsA get fails
    await expect(getSalesOpportunityService(oppB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    // wsA update fails
    await expect(updateOpportunityStageService(oppB.id, "WON", wsA.ctx)).rejects.toThrow(/not found/i);
    await expect(
      updateOpportunityStage({
        id: oppB.id,
        stage: "WON",
        workspaceId: wsA.workspaceId,
        authorization: wsA.authorization,
      })
    ).rejects.toThrow(/not found/i);

    // Verify record B was not mutated
    const stillDiscovery = await getSalesOpportunityService(oppB.id, wsB.ctx);
    expect(stillDiscovery.stage).toBe("DISCOVERY");
  });
});
