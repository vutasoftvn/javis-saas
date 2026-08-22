import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createSalesLead, getSalesLead, listSalesLeads, updateLeadStage } from "./lead";

describe("createSalesLead", () => {
  it("creates a lead with the default NEW stage", async () => {
    const workspace = await createWorkspace({ name: "Lead Test Inc" });
    const lead = await createSalesLead({ workspaceId: workspace.id, name: "Interested Prospect" });
    expect(lead.id).toBeGreaterThan(0);
    expect(lead.stage).toBe("NEW");
  });

  it("rejects a lead for a workspace that doesn't exist", async () => {
    await expect(createSalesLead({ workspaceId: 999999999, name: "Orphan Lead" })).rejects.toThrow();
  });
});

describe("getSalesLead/listSalesLeads", () => {
  it("fetches a created lead and lists it by workspace", async () => {
    const workspace = await createWorkspace({ name: "List Lead Test Inc" });
    const created = await createSalesLead({ workspaceId: workspace.id, name: "Fetch me" });

    const fetched = await getSalesLead({ id: created.id });
    expect(fetched).toEqual(created);

    const { leads } = await listSalesLeads({ workspaceId: workspace.id });
    expect(leads.map((l) => l.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getSalesLead({ id: 999999999 })).rejects.toThrow();
  });
});

describe("updateLeadStage", () => {
  it("transitions a lead's stage", async () => {
    const workspace = await createWorkspace({ name: "Stage Lead Test Inc" });
    const created = await createSalesLead({ workspaceId: workspace.id, name: "Progressing lead" });

    const qualified = await updateLeadStage({ id: created.id, stage: "QUALIFIED" });
    expect(qualified.stage).toBe("QUALIFIED");
  });

  it("throws not found for a missing id", async () => {
    await expect(updateLeadStage({ id: 999999999, stage: "QUALIFIED" })).rejects.toThrow();
  });
});
