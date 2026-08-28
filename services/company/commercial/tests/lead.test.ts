import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createSalesLead, getSalesLead, listSalesLeads, updateLeadStage } from "../handlers/lead.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createSalesLead", () => {
  it("creates a lead with the default NEW stage", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Lead Test Inc");
    const lead = await createSalesLead({ workspaceId, name: "Interested Prospect", authorization });
    expect(lead.id).toBeDefined();
    expect(lead.stage).toBe("NEW");
  });

  it("rejects a lead for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Lead Test");
    await expect(
      createSalesLead({ workspaceId: "999999999", name: "Orphan Lead", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Lead Ws");
    const outsider = await makeAuthedWorkspace("Outsider Lead Test");
    await expect(
      createSalesLead({ workspaceId, name: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getSalesLead/listSalesLeads", () => {
  it("fetches a created lead and lists it by workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("List Lead Test Inc");
    const created = await createSalesLead({ workspaceId, name: "Fetch me", authorization });

    const fetched = await getSalesLead({ id: created.id, workspaceId, authorization });
    expect(fetched).toEqual(created);

    const { leads } = await listSalesLeads({ workspaceId, authorization });
    expect(leads.map((l) => l.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Lead Test");
    await expect(getSalesLead({ id: "999999999", workspaceId, authorization })).rejects.toThrow();
  });
});

describe("updateLeadStage", () => {
  it("transitions a lead's stage", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Stage Lead Test Inc");
    const created = await createSalesLead({ workspaceId, name: "Progressing lead", authorization });

    const qualified = await updateLeadStage({ id: created.id, stage: "QUALIFIED", workspaceId, authorization });
    expect(qualified.stage).toBe("QUALIFIED");
  });

  it("throws not found for a missing id", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Lead Stage Test");
    await expect(updateLeadStage({ id: "999999999", stage: "QUALIFIED", workspaceId, authorization })).rejects.toThrow();
  });
});

