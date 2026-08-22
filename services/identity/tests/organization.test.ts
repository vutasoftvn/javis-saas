import { describe, expect, it } from "vitest";
import { createWorkspace } from "../handlers/workspace.handler";
import {
  createOrganization,
  hireWorkforceMember,
  getWorkforceMember,
} from "../handlers/organization.handler";

describe("createOrganization", () => {
  it("creates one organization per workspace", async () => {
    const workspace = await createWorkspace({ name: "Org Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "Org Test Inc" });
    expect(org.id).toBeGreaterThan(0);
    expect(org.workspaceId).toBe(workspace.id);
  });
});

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const workspace = await createWorkspace({ name: "Hire Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "Hire Test Inc" });

    const member = await hireWorkforceMember({
      organizationId: org.id,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
    });
    expect(member.id).toBeGreaterThan(0);
    expect(member.memberType).toBe("HUMAN");
    expect(member.status).toBe("active");

    const fetched = await getWorkforceMember({ id: member.id });
    expect(fetched).toEqual(member);
  });

  it("hires an AI_AGENT member with an agentDefinitionId reference", async () => {
    const workspace = await createWorkspace({ name: "AI Hire Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "AI Hire Test Inc" });

    const member = await hireWorkforceMember({
      organizationId: org.id,
      memberType: "AI_AGENT",
      roleTitle: "CFO Agent",
      agentDefinitionId: 42,
    });
    expect(member.agentDefinitionId).toBe(42);
  });

  it("throws not found for a missing member id", async () => {
    await expect(getWorkforceMember({ id: 999999999 })).rejects.toThrow();
  });
});
