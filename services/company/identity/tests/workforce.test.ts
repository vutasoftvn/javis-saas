import { describe, expect, it } from "vitest";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";
import { createTestSession } from "./helpers/test-session";

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const session = await createTestSession({ displayName: "Hire Test Owner" });
    const authorization = `Bearer ${session.accessToken}`;

    const member = await hireWorkforceMember({
      workspaceId: session.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: session.userId,
      authorization,
    });
    expect(member.id).toBeTruthy();
    expect(typeof member.id).toBe("string");
    expect(member.memberType).toBe("HUMAN");
    expect(member.workspaceId).toBe(session.workspaceId);
    expect(member.humanUserId).toBe(session.userId);
    expect(member.status).toBe("active");

    const fetched = await getWorkforceMember({
      id: member.id,
      workspaceId: session.workspaceId,
      authorization,
    });
    expect(fetched).toEqual(member);
  });

  it("hires an AI_AGENT member with an agentSpecId + agentSpecVersion reference", async () => {
    const session = await createTestSession({ displayName: "AI Hire Test Owner" });
    const authorization = `Bearer ${session.accessToken}`;

    const member = await hireWorkforceMember({
      workspaceId: session.workspaceId,
      memberType: "AI_AGENT",
      roleTitle: "CFO Agent",
      agentSpecId: "finance-cfo",
      agentSpecVersion: "1.0",
      authorization,
    });
    expect(member.agentSpecId).toBe("finance-cfo");
    expect(member.agentSpecVersion).toBe("1.0");
    expect(member.humanUserId).toBeNull();
  });

  it("supports a manager hierarchy via managerMemberId", async () => {
    const managerSession = await createTestSession({ displayName: "VP Ops" });
    const reportSession = await createTestSession({ displayName: "Ops Associate" });
    const authorization = `Bearer ${managerSession.accessToken}`;
    const manager = await hireWorkforceMember({
      workspaceId: managerSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "VP Ops",
      humanUserId: managerSession.userId,
      authorization,
    });
    const report = await hireWorkforceMember({
      workspaceId: managerSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Associate",
      humanUserId: reportSession.userId,
      managerMemberId: manager.id,
      authorization,
    });
    expect(report.managerMemberId).toBe(manager.id);
  });

  it("throws not found for a missing member id", async () => {
    const session = await createTestSession({ displayName: "Missing Id Owner" });
    await expect(
      getWorkforceMember({
        id: "999999999",
        workspaceId: session.workspaceId,
        authorization: `Bearer ${session.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("M1 §3: a member of another workspace is notFound, not disclosed", async () => {
    const owner = await createTestSession({ displayName: "WS A Owner" });
    const outsider = await createTestSession({ displayName: "WS B Owner" });

    const member = await hireWorkforceMember({
      workspaceId: owner.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: owner.userId,
      authorization: `Bearer ${owner.accessToken}`,
    });

    // Outsider authenticates in THEIR OWN workspace but asks for A's member id.
    await expect(
      getWorkforceMember({
        id: member.id,
        workspaceId: outsider.workspaceId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow(/not found/i);
  });

  it("rejects a HUMAN member without humanUserId", async () => {
    const session = await createTestSession({ displayName: "Missing Human User Owner" });
    await expect(
      hireWorkforceMember({
        workspaceId: session.workspaceId,
        memberType: "HUMAN",
        roleTitle: "Ops Lead",
        authorization: `Bearer ${session.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects an AI_AGENT member without agentSpecId/agentSpecVersion", async () => {
    const session = await createTestSession({ displayName: "Missing Agent Spec Owner" });
    await expect(
      hireWorkforceMember({
        workspaceId: session.workspaceId,
        memberType: "AI_AGENT",
        roleTitle: "CFO Agent",
        authorization: `Bearer ${session.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects a member being their own manager", async () => {
    const session = await createTestSession({ displayName: "Self Manager Owner" });
    const member = await hireWorkforceMember({
      workspaceId: session.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Solo Founder",
      humanUserId: session.userId,
      authorization: `Bearer ${session.accessToken}`,
    });

    // Không có API update managerMemberId — verify bằng cách insert trực tiếp
    // qua DB để chứng minh CHECK chặn ở tầng DB.
    const { db, schema } = await import("../models/db");
    const { eq } = await import("drizzle-orm");
    await expect(
      db
        .update(schema.identityWorkforceMembers)
        .set({ managerMemberId: BigInt(member.id) })
        .where(eq(schema.identityWorkforceMembers.id, BigInt(member.id)))
    ).rejects.toThrow();
  });

  it("rejects a manager from a different workspace", async () => {
    const ownerSession = await createTestSession({ displayName: "Cross WS Owner" });
    const otherSession = await createTestSession({ displayName: "Other WS Owner" });

    const manager = await hireWorkforceMember({
      workspaceId: otherSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Outside Manager",
      humanUserId: otherSession.userId,
      authorization: `Bearer ${otherSession.accessToken}`,
    });

    await expect(
      hireWorkforceMember({
        workspaceId: ownerSession.workspaceId,
        memberType: "HUMAN",
        roleTitle: "Report",
        humanUserId: ownerSession.userId,
        managerMemberId: manager.id,
        authorization: `Bearer ${ownerSession.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects hiring a workforce member without a valid authorization for that workspace", async () => {
    const owner = await createTestSession({ displayName: "Hire Auth Owner" });
    const outsider = await createTestSession({ displayName: "Hire Auth Outsider" });

    await expect(
      hireWorkforceMember({
        workspaceId: owner.workspaceId,
        memberType: "HUMAN",
        roleTitle: "Ops Lead",
        humanUserId: owner.userId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects reading a workforce member without a valid authorization for that workspace", async () => {
    const owner = await createTestSession({ displayName: "Read Auth Owner" });
    const outsider = await createTestSession({ displayName: "Read Auth Outsider" });

    const member = await hireWorkforceMember({
      workspaceId: owner.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: owner.userId,
      authorization: `Bearer ${owner.accessToken}`,
    });

    await expect(
      getWorkforceMember({
        id: member.id,
        workspaceId: owner.workspaceId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();
  });
});
