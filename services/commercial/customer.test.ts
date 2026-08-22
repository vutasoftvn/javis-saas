import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createSalesOpportunity } from "./opportunity";
import { createCustomer, getCustomer } from "./customer";

describe("createCustomer", () => {
  it("creates a customer with the default ONBOARDING lifecycle status", async () => {
    const workspace = await createWorkspace({ name: "Customer Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const customer = await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    expect(customer.id).toBeGreaterThan(0);
    expect(customer.lifecycleStatus).toBe("ONBOARDING");
    expect(customer.healthStatus).toBe("HEALTHY");
  });

  it("links a customer back to the opportunity it was acquired from", async () => {
    const workspace = await createWorkspace({ name: "Acquired Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acquired Corp" });
    const opportunity = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });

    const customer = await createCustomer({
      workspaceId: workspace.id,
      accountId: account.id,
      acquiredFromOpportunityId: opportunity.id,
    });
    expect(customer.acquiredFromOpportunityId).toBe(opportunity.id);
  });

  it("rejects a second customer for the same account in the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "One Customer Corp" });
    await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    await expect(createCustomer({ workspaceId: workspace.id, accountId: account.id })).rejects.toThrow();
  });
});

describe("getCustomer", () => {
  it("fetches a previously created customer", async () => {
    const workspace = await createWorkspace({ name: "Fetch Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Fetch Account" });
    const created = await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    const fetched = await getCustomer({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getCustomer({ id: 999999999 })).rejects.toThrow();
  });
});
