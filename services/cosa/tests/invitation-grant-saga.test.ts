import { afterEach, describe, expect, it, vi } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreOrganization from "../services/core-organization.service";
import { projectCoreAccess, projectCoreUser } from "../services/core-projection.service";
import {
  acceptWorkspaceInvitation,
  createWorkspaceInvitation,
  reconcileInvitationGrants,
} from "../services/workspace-invitation.service";

// Spec 2026-09-25 §8 — saga cấp membership: ghi ý định trước khi gọi core,
// kết quả mơ hồ (core thành công nhưng chiếu cục bộ chưa xong) phải phục hồi
// được bằng retry hoặc reconciler, không bao giờ tạo membership thứ hai.

const { workspaceMemberships, workspaceInvitations, organizationInvitationGrants } = schema;

async function setup() {
  const founderId = generateSnowflakeStr();
  const inviteeId = generateSnowflakeStr();
  const orgId = generateSnowflakeStr();
  const inviteeEmail = `saga-${inviteeId}@core.test`;
  await projectCoreAccess({
    user: { userId: founderId, email: `founder-${founderId}@core.test`, displayName: "Founder" },
    organization: { organizationId: orgId, name: "Saga Co", ownerUserId: founderId },
    role: "founder",
  });
  await projectCoreUser({ userId: inviteeId, email: inviteeEmail, displayName: "Invitee" });
  const invitation = await createWorkspaceInvitation(founderId, {
    workspace_id: orgId,
    email: inviteeEmail,
    role_id: "member",
  });
  const [inv] = await db
    .select({ id: workspaceInvitations.id })
    .from(workspaceInvitations)
    .where(eq(workspaceInvitations.organizationId, BigInt(orgId)));
  return { inviteeId, orgId, token: invitation.token, invitationId: inv.id };
}

async function grantsFor(invitationId: bigint) {
  return db.select().from(organizationInvitationGrants).where(eq(organizationInvitationGrants.invitationId, invitationId));
}

async function membershipsFor(orgId: string, userId: string) {
  return db
    .select()
    .from(workspaceMemberships)
    .where(and(eq(workspaceMemberships.organizationId, BigInt(orgId)), eq(workspaceMemberships.userId, BigInt(userId))));
}

describe("invitation grant saga", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("đi đúng requested -> core_granted -> projected và lưu version core trả về", async () => {
    const { inviteeId, orgId, token, invitationId } = await setup();
    vi.spyOn(coreOrganization, "grantCoreMembership").mockResolvedValue({ role: "member", membershipVersion: 7 });

    await acceptWorkspaceInvitation(inviteeId, { token });

    const [grant] = await grantsFor(invitationId);
    expect(grant.state).toBe("projected");
    expect(grant.coreRole).toBe("member");
    expect(Number(grant.coreMembershipVersion)).toBe(7);
    expect(await membershipsFor(orgId, inviteeId)).toHaveLength(1);
  });

  it("core lỗi rồi retry: dùng lại đúng một grant, không nhân đôi membership", async () => {
    const { inviteeId, orgId, token, invitationId } = await setup();
    const spy = vi
      .spyOn(coreOrganization, "grantCoreMembership")
      .mockRejectedValueOnce(Object.assign(new Error("timeout"), { code: "unavailable" }))
      .mockResolvedValueOnce({ role: "member", membershipVersion: 1 });

    await expect(acceptWorkspaceInvitation(inviteeId, { token })).rejects.toMatchObject({ code: "unavailable" });
    let grants = await grantsFor(invitationId);
    expect(grants).toHaveLength(1);
    expect(grants[0].state).toBe("requested");
    expect(grants[0].lastErrorCode).toBe("unavailable");

    await acceptWorkspaceInvitation(inviteeId, { token });
    // Retry lần ba sau khi đã thành công chỉ trả lại membership hiện có.
    await acceptWorkspaceInvitation(inviteeId, { token });

    expect(spy).toHaveBeenCalledTimes(2);
    grants = await grantsFor(invitationId);
    expect(grants).toHaveLength(1);
    expect(grants[0].state).toBe("projected");
    expect(grants[0].attempts).toBe(2);
    expect(await membershipsFor(orgId, inviteeId)).toHaveLength(1);
  });

  it("core đã cấp nhưng chiếu cục bộ chưa xong: retry chỉ chiếu, không gọi core lần nữa", async () => {
    const { inviteeId, orgId, token, invitationId } = await setup();
    await db.insert(organizationInvitationGrants).values({
      id: BigInt(generateSnowflakeStr()),
      invitationId,
      organizationId: BigInt(orgId),
      userId: BigInt(inviteeId),
      requestedRole: "member",
      state: "core_granted",
      coreRole: "member",
    });
    const spy = vi.spyOn(coreOrganization, "grantCoreMembership");

    const res = await acceptWorkspaceInvitation(inviteeId, { token });

    expect(spy).not.toHaveBeenCalled();
    expect(res.role_id).toBe("member");
    const [inv] = await db.select().from(workspaceInvitations).where(eq(workspaceInvitations.id, invitationId));
    expect(inv.status).toBe("accepted");
    expect((await grantsFor(invitationId))[0].state).toBe("projected");
  });

  it("reconciler chiếu grant core_granted bị bỏ dở", async () => {
    const { inviteeId, orgId, invitationId } = await setup();
    await db.insert(organizationInvitationGrants).values({
      id: BigInt(generateSnowflakeStr()),
      invitationId,
      organizationId: BigInt(orgId),
      userId: BigInt(inviteeId),
      requestedRole: "member",
      state: "core_granted",
      coreRole: "member",
      updatedAt: new Date(Date.now() - 10 * 60_000),
    });

    await reconcileInvitationGrants({ minAgeMs: 60_000, limit: 500 });

    expect((await grantsFor(invitationId))[0].state).toBe("projected");
    expect(await membershipsFor(orgId, inviteeId)).toHaveLength(1);
  });

  it("reconciler hỏi lại core cho grant requested còn hiệu lực, giữ nguyên khi core vẫn lỗi", async () => {
    const { inviteeId, orgId, invitationId } = await setup();
    await db.insert(organizationInvitationGrants).values({
      id: BigInt(generateSnowflakeStr()),
      invitationId,
      organizationId: BigInt(orgId),
      userId: BigInt(inviteeId),
      requestedRole: "member",
      state: "requested",
      updatedAt: new Date(Date.now() - 10 * 60_000),
    });
    const spy = vi.spyOn(coreOrganization, "grantCoreMembership").mockImplementation(async (org) => {
      if (org === orgId) throw Object.assign(new Error("core down"), { code: "unavailable" });
      return { role: "member" };
    });

    await reconcileInvitationGrants({ minAgeMs: 60_000, limit: 500 });

    expect(spy).toHaveBeenCalledWith(orgId, inviteeId, "member");
    const [grant] = await grantsFor(invitationId);
    expect(grant.state).toBe("requested");
    expect(await membershipsFor(orgId, inviteeId)).toHaveLength(0);
  });

  it("reconciler đánh dấu failed khi lời mời không còn pending, không gọi core", async () => {
    const { inviteeId, orgId, invitationId } = await setup();
    await db.update(workspaceInvitations).set({ status: "revoked" }).where(eq(workspaceInvitations.id, invitationId));
    await db.insert(organizationInvitationGrants).values({
      id: BigInt(generateSnowflakeStr()),
      invitationId,
      organizationId: BigInt(orgId),
      userId: BigInt(inviteeId),
      requestedRole: "member",
      state: "requested",
      updatedAt: new Date(Date.now() - 10 * 60_000),
    });
    const spy = vi.spyOn(coreOrganization, "grantCoreMembership").mockResolvedValue({ role: "member" });

    await reconcileInvitationGrants({ minAgeMs: 60_000, limit: 500 });

    expect(spy).not.toHaveBeenCalledWith(orgId, inviteeId, "member");
    const [grant] = await grantsFor(invitationId);
    expect(grant.state).toBe("failed");
    expect(grant.lastErrorCode).toBe("invitation_not_pending");
    expect(await membershipsFor(orgId, inviteeId)).toHaveLength(0);
  });
});
