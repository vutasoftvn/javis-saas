import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createAccount } from "../handlers/account.handler";
import { createSalesOpportunity, getSalesOpportunity, updateOpportunityStage } from "../handlers/opportunity.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createSalesOpportunity", () => {
  it("creates an opportunity with the default DISCOVERY stage and VND currency", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Opportunity Test Inc");
    const account = await createAccount({ workspaceId, name: "Acme Corp", authorization });
    const opportunity = await createSalesOpportunity({ workspaceId, accountId: account.id, authorization });
    expect(opportunity.id).toBeDefined();
    expect(opportunity.stage).toBe("DISCOVERY");
    expect(opportunity.currency).toBe("VND");
  });

  it("rejects an opportunity for an account that doesn't exist (real DB FK)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Bad Account Opp Inc");
    await expect(
      createSalesOpportunity({ workspaceId, accountId: "999999999", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Owner Opp Ws");
    const account = await createAccount({ workspaceId, name: "Owner Acct", authorization });
    const outsider = await makeAuthedWorkspace("Outsider Opp Test");
    await expect(
      createSalesOpportunity({ workspaceId, accountId: account.id, authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getSalesOpportunity", () => {
  it("fetches a previously created opportunity", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Opp Inc");
    const account = await createAccount({ workspaceId, name: "Fetch Account", authorization });
    const created = await createSalesOpportunity({ workspaceId, accountId: account.id, authorization });
    const fetched = await getSalesOpportunity({ id: created.id, workspaceId, authorization });
    expect(fetched).toEqual(created);
  });
});

describe("updateOpportunityStage", () => {
  it("transitions an opportunity's stage", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Stage Opp Inc");
    const account = await createAccount({ workspaceId, name: "Stage Account", authorization });
    const created = await createSalesOpportunity({ workspaceId, accountId: account.id, authorization });

    const won = await updateOpportunityStage({ id: created.id, stage: "WON", workspaceId, authorization });
    expect(won.stage).toBe("WON");
  });
});

