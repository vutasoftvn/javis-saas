import { describe, expect, it } from "vitest";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";
import { createTestSession } from "./helpers/test-session";

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const session = await createTestSession({ displayName: "Hire Test Owner" });

    const member = await hireWorkforceMember({
      workspaceId: session.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: session.userId,
    });
    expect(member.id).toBeTruthy();
    expect(typeof member.id).toBe("string");
    expect(member.memberType).toBe("HUMAN");
    expect(member.workspaceId).toBe(session.workspaceId);
    expect(member.humanUserId).toBe(session.userId);
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
    const managerSession = await createTestSession({ displayName: "VP Ops" });
    const reportSession = await createTestSession({ displayName: "Ops Associate" });
    const manager = await hireWorkforceMember({
      workspaceId: managerSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "VP Ops",
      humanUserId: managerSession.userId,
    });
    const report = await hireWorkforceMember({
      workspaceId: managerSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Associate",
      humanUserId: reportSession.userId,
      managerMemberId: manager.id,
    });
    expect(report.managerMemberId).toBe(manager.id);
  });

  it("throws not found for a missing member id", async () => {
    await expect(getWorkforceMember({ id: "999999999" })).rejects.toThrow();
  });

  it("rejects a HUMAN member without humanUserId", async () => {
    const workspace = await createWorkspace({ name: "Missing Human User Inc" });
    await expect(
      hireWorkforceMember({ workspaceId: workspace.id, memberType: "HUMAN", roleTitle: "Ops Lead" })
    ).rejects.toThrow();
  });

  it("rejects an AI_AGENT member without agentSpecId/agentSpecVersion", async () => {
    const workspace = await createWorkspace({ name: "Missing Agent Spec Inc" });
    await expect(
      hireWorkforceMember({ workspaceId: workspace.id, memberType: "AI_AGENT", roleTitle: "CFO Agent" })
    ).rejects.toThrow();
  });
});
