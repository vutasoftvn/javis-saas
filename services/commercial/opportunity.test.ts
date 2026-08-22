import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createSalesOpportunity, getSalesOpportunity, updateOpportunityStage } from "./opportunity";

describe("createSalesOpportunity", () => {
  it("creates an opportunity with the default DISCOVERY stage and VND currency", async () => {
    const workspace = await createWorkspace({ name: "Opportunity Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const opportunity = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });
    expect(opportunity.id).toBeGreaterThan(0);
    expect(opportunity.stage).toBe("DISCOVERY");
    expect(opportunity.currency).toBe("VND");
  });

  it("rejects an opportunity for an account that doesn't exist (real DB FK)", async () => {
    const workspace = await createWorkspace({ name: "Bad Account Opp Inc" });
    await expect(
      createSalesOpportunity({ workspaceId: workspace.id, accountId: 999999999 })
    ).rejects.toThrow();
  });
});

describe("getSalesOpportunity", () => {
  it("fetches a previously created opportunity", async () => {
    const workspace = await createWorkspace({ name: "Fetch Opp Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Fetch Account" });
    const created = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });
    const fetched = await getSalesOpportunity({ id: created.id });
    expect(fetched).toEqual(created);
  });
});

describe("updateOpportunityStage", () => {
  it("transitions an opportunity's stage", async () => {
    const workspace = await createWorkspace({ name: "Stage Opp Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Stage Account" });
    const created = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });

    const won = await updateOpportunityStage({ id: created.id, stage: "WON" });
    expect(won.stage).toBe("WON");
  });
});
