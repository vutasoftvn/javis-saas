import { describe, expect, it } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { createAccount } from "../handlers/account.handler";
import { createSalesOpportunity } from "../handlers/opportunity.handler";
import { createCustomer, getCustomer } from "../handlers/customer.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createCustomer", () => {
  it("creates a customer with the default ONBOARDING lifecycle status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Customer Test Inc");
    const account = await createAccount({ workspaceId, name: "Acme Corp", authorization });
    const customer = await createCustomer({ workspaceId, accountId: account.id, authorization });
    expect(customer.id).toBeGreaterThan(0);
    expect(customer.lifecycleStatus).toBe("ONBOARDING");
    expect(customer.healthStatus).toBe("HEALTHY");
  });

  it("links a customer back to the opportunity it was acquired from", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Acquired Customer Inc");
    const account = await createAccount({ workspaceId, name: "Acquired Corp", authorization });
    const opportunity = await createSalesOpportunity({ workspaceId, accountId: account.id, authorization });

    const customer = await createCustomer({
      workspaceId,
      accountId: account.id,
      acquiredFromOpportunityId: opportunity.id,
      authorization,
    });
    expect(customer.acquiredFromOpportunityId).toBe(opportunity.id);
  });

  it("rejects a second customer for the same account in the same workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Dup Customer Inc");
    const account = await createAccount({ workspaceId, name: "One Customer Corp", authorization });
    await createCustomer({ workspaceId, accountId: account.id, authorization });
    await expect(createCustomer({ workspaceId, accountId: account.id, authorization })).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Owner Customer Ws");
    const account = await createAccount({ workspaceId, name: "Owner Acct", authorization });
    const outsider = await makeAuthedWorkspace("Outsider Customer Test");
    await expect(
      createCustomer({ workspaceId, accountId: account.id, authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getCustomer", () => {
  it("fetches a previously created customer", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Customer Inc");
    const account = await createAccount({ workspaceId, name: "Fetch Account", authorization });
    const created = await createCustomer({ workspaceId, accountId: account.id, authorization });
    const fetched = await getCustomer({ id: created.id, authorization });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Customer Test");
    await expect(getCustomer({ id: 999999999, authorization })).rejects.toThrow();
  });
});
