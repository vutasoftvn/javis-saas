import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreOrganization from "../services/core-organization.service";
import { projectCoreAccess, projectCoreUser } from "../services/core-projection.service";
import { acceptWorkspaceInvitation, createWorkspaceInvitation } from "../services/workspace-invitation.service";

const { workspaceMemberships, workspaceInvitations } = schema;

async function setup() {
  const founderId = generateSnowflakeStr();
  const inviteeId = generateSnowflakeStr();
  const orgId = generateSnowflakeStr();
  const inviteeEmail = `invitee-${inviteeId}@core.test`;

  await projectCoreAccess({
    user: { userId: founderId, email: `founder-${founderId}@core.test`, displayName: "Founder" },
    organization: { organizationId: orgId, name: "Invite Co", ownerUserId: founderId },
    role: "founder",
  });
  await projectCoreUser({ userId: inviteeId, email: inviteeEmail, displayName: "Invitee" });

  const invitation = await createWorkspaceInvitation(founderId, {
    workspace_id: orgId,
    email: inviteeEmail,
    role_id: "member",
  });
  return { founderId, inviteeId, orgId, token: invitation.token };
}

describe("acceptWorkspaceInvitation qua core", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("cấp membership ở core rồi mới ghi membership cục bộ theo role core trả về", async () => {
    const { inviteeId, orgId, token } = await setup();
    const grant = vi.spyOn(coreOrganization, "grantCoreMembership").mockResolvedValue({ role: "member" });

    const res = await acceptWorkspaceInvitation(inviteeId, { token });

    expect(grant).toHaveBeenCalledWith(orgId, inviteeId, "member");
    expect(res).toMatchObject({ company_id: orgId, role_id: "member" });
    const [m] = await db
      .select()
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.workspaceId, BigInt(orgId)), eq(workspaceMemberships.userId, BigInt(inviteeId))));
    expect(m.roleId).toBe("member");
    const [inv] = await db.select().from(workspaceInvitations).where(eq(workspaceInvitations.workspaceId, BigInt(orgId)));
    expect(inv.status).toBe("accepted");
  });

  it("dùng role hiện có ở core nếu người dùng đã là thành viên (đã được quy về role cosa)", async () => {
    const { inviteeId, orgId, token } = await setup();
    vi.spyOn(coreOrganization, "grantCoreMembership").mockResolvedValue({ role: "owner" });

    const res = await acceptWorkspaceInvitation(inviteeId, { token });

    expect(res.role_id).toBe("founder");
    const [m] = await db
      .select()
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.workspaceId, BigInt(orgId)), eq(workspaceMemberships.userId, BigInt(inviteeId))));
    expect(m.roleId).toBe("founder");
  });

  it("core lỗi: rollback, lời mời vẫn pending và chưa có membership", async () => {
    const { inviteeId, orgId, token } = await setup();
    vi.spyOn(coreOrganization, "grantCoreMembership").mockRejectedValue(
      Object.assign(new Error("core down"), { code: "unavailable" })
    );

    await expect(acceptWorkspaceInvitation(inviteeId, { token })).rejects.toMatchObject({
      code: "unavailable",
    });

    const members = await db
      .select()
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.workspaceId, BigInt(orgId)), eq(workspaceMemberships.userId, BigInt(inviteeId))));
    expect(members).toHaveLength(0);
    const [inv] = await db.select().from(workspaceInvitations).where(eq(workspaceInvitations.workspaceId, BigInt(orgId)));
    expect(inv.status).toBe("pending");
  });

  it("email không khớp: từ chối trước khi gọi core", async () => {
    const { orgId, token } = await setup();
    const strangerId = generateSnowflakeStr();
    await projectCoreUser({ userId: strangerId, email: `stranger-${strangerId}@core.test` });
    const grant = vi.spyOn(coreOrganization, "grantCoreMembership");

    await expect(acceptWorkspaceInvitation(strangerId, { token })).rejects.toMatchObject({
      code: "permission_denied",
    });
    expect(grant).not.toHaveBeenCalled();
    expect(orgId).toBeTruthy();
  });
});

describe("grantCoreMembership", () => {
  const fetchMock = vi.fn();
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

  beforeEach(() => {
    process.env.CORE_BASE_URL = "http://core.test";
    process.env.CORE_INTROSPECT_CLIENT_ID = "vn.mivacorp.cosa.backend";
    process.env.CORE_INTROSPECT_CLIENT_SECRET = "s3cret";
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("gọi endpoint nội bộ của core bằng client credentials của backend COSA", async () => {
    fetchMock.mockResolvedValueOnce(json({ role: "member", membershipVersion: 2 }));

    const result = await coreOrganization.grantCoreMembership("100", "42", "member");

    expect(result).toEqual({ role: "member" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://core.test/internal/organizations/100/members");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe(
      "Basic " + Buffer.from("vn.mivacorp.cosa.backend:s3cret").toString("base64")
    );
    expect(JSON.parse(init.body)).toEqual({ userId: "42", role: "member" });
  });

  it("401/403 -> internal (lỗi cấu hình), 404 -> not_found, 5xx hoặc mạng -> unavailable", async () => {
    fetchMock.mockResolvedValueOnce(json({}, 401));
    await expect(coreOrganization.grantCoreMembership("1", "2", "member")).rejects.toMatchObject({ code: "internal" });
    fetchMock.mockResolvedValueOnce(json({}, 403));
    await expect(coreOrganization.grantCoreMembership("1", "2", "member")).rejects.toMatchObject({ code: "internal" });
    fetchMock.mockResolvedValueOnce(json({}, 404));
    await expect(coreOrganization.grantCoreMembership("1", "2", "member")).rejects.toMatchObject({ code: "not_found" });
    fetchMock.mockResolvedValueOnce(json({}, 500));
    await expect(coreOrganization.grantCoreMembership("1", "2", "member")).rejects.toMatchObject({ code: "unavailable" });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(coreOrganization.grantCoreMembership("1", "2", "member")).rejects.toMatchObject({ code: "unavailable" });
  });
});
