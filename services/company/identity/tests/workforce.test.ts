import { describe, expect, it } from "vitest";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const workspace = await createWorkspace({ name: "Hire Test Inc" });

    const member = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
    });
    expect(member.id).toBeTruthy();
    expect(typeof member.id).toBe("string");
    expect(member.memberType).toBe("HUMAN");
    expect(member.workspaceId).toBe(workspace.id);
    expect(member.status).toBe("active");

    const fetched = await getWorkforceMember({ id: member.id });
    expect(fetched).toEqual(member);
  });

  it("hires an AI_AGENT member with an agentSpecId + agentSpecVersion reference", async () => {
    const workspace = await createWorkspace({ name: "AI Hire Test Inc" });

    const member = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "AI_AGENT",
      roleTitle: "CFO Agent",
      agentSpecId: "finance-cfo",
      agentSpecVersion: "1.0",
    });
    expect(member.agentSpecId).toBe("finance-cfo");
    expect(member.agentSpecVersion).toBe("1.0");
    expect(member.humanUserId).toBeNull();
  });

  it("supports a manager hierarchy via managerMemberId", async () => {
    const workspace = await createWorkspace({ name: "Hierarchy Test Inc" });
    const manager = await hireWorkforceMember({ workspaceId: workspace.id, memberType: "HUMAN", roleTitle: "VP Ops" });
    const report = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "HUMAN",
      roleTitle: "Ops Associate",
      managerMemberId: manager.id,
    });
    expect(report.managerMemberId).toBe(manager.id);
  });

  it("throws not found for a missing member id", async () => {
    await expect(getWorkforceMember({ id: "999999999" })).rejects.toThrow();
  });
});
