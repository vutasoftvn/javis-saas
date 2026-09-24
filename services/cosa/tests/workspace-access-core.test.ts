import { afterEach, describe, expect, it, vi } from "vitest";
import { APIError } from "encore.dev/api";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreIntrospect from "../services/core-introspect.service";
import * as coreOrganization from "../services/core-organization.service";
import { projectCoreAccess } from "../services/core-projection.service";
import {
  listMembershipsForToken,
  validateMembershipForToken,
} from "../services/workspace-access.service";
import { resolveCallerAuthorizedForWorkspace, verifyWorkspaceMembership } from "../services/workspace-connector.service";
import { validateUserMembership } from "../services/company.service";

const info = (userId: string) => ({
  userId,
  clientId: "vn.mivacorp.cosa",
  scopes: ["openid"],
  expiresAt: 9999999999,
  email: `wa-${userId}@core.test`,
  displayName: "Member",
});

function coreAllows(userId: string, orgId: string, role = "founder", name = "Org") {
  vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));
  return vi.spyOn(coreOrganization, "authorizeCoreOrganizationAction").mockImplementation(async (_t, id) => {
    if (id !== orgId) throw APIError.permissionDenied("not a member");
    return { role, membershipVersion: 2, typeCode: null, organizationName: name, ownerUserId: userId };
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("validateMembershipForToken (token core)", () => {
  it("core cho phép: chiếu và trả membership cục bộ", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    coreAllows(userId, orgId, "admin", "Acme");

    const result = await validateMembershipForToken("opaque", orgId);

    expect(result.userId).toBe(userId);
    expect(result.membership).toMatchObject({ platformWorkspaceId: orgId, workspaceName: "Acme", role: "admin" });
  });

  it("core từ chối (không phải thành viên): membership = null, không ném lỗi", async () => {
    const userId = generateSnowflakeStr();
    coreAllows(userId, generateSnowflakeStr());

    const result = await validateMembershipForToken("opaque", generateSnowflakeStr());

    expect(result.membership).toBeNull();
  });

  it("token core sai -> unauthenticated nổi lên", async () => {
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockRejectedValue(
      Object.assign(new Error("bad"), { code: "unauthenticated" })
    );
    await expect(validateMembershipForToken("opaque", "1")).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

describe("listMembershipsForToken (token core)", () => {
  it("chỉ trả organization còn hiệu lực ở core, bỏ bản chiếu cũ đã bị thu hồi", async () => {
    const userId = generateSnowflakeStr();
    const live = generateSnowflakeStr();
    const revoked = generateSnowflakeStr();
    // Bản chiếu cũ của một organization đã bị thu hồi ở core.
    await projectCoreAccess({
      user: { userId, email: `wa-${userId}@core.test`, displayName: "Member" },
      organization: { organizationId: revoked, name: "Old", ownerUserId: userId },
      role: "member",
    });
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));
    vi.spyOn(coreOrganization, "listCoreOrganizations").mockResolvedValue([
      { organizationId: live, name: "Live", role: "founder" },
    ]);
    vi.spyOn(coreOrganization, "authorizeCoreOrganizationAction").mockResolvedValue({
      role: "founder",
      membershipVersion: 1,
      typeCode: null,
      organizationName: "Live",
      ownerUserId: userId,
    });

    const memberships = await listMembershipsForToken("opaque");

    expect(memberships.map((m) => m.platformWorkspaceId)).toEqual([live]);
    expect(memberships[0]).toMatchObject({ workspaceName: "Live", role: "founder", userId });
  });
});

describe("verifyWorkspaceMembership / resolveCallerAuthorizedForWorkspace (token core)", () => {
  it("verifyWorkspaceMembership hỏi core thay vì services/company", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    coreAllows(userId, orgId, "member");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const info2 = await verifyWorkspaceMembership(orgId, "Bearer opaque");

    expect(info2).toEqual({ platformCompanyId: null, membershipRole: "member" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("verifyWorkspaceMembership: core từ chối -> permission_denied", async () => {
    coreAllows(generateSnowflakeStr(), generateSnowflakeStr());
    await expect(verifyWorkspaceMembership(generateSnowflakeStr(), "Bearer opaque")).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  it("resolveCallerAuthorizedForWorkspace trả sub là user id của core", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    coreAllows(userId, orgId);

    expect(await resolveCallerAuthorizedForWorkspace("Bearer opaque", orgId)).toEqual({ sub: userId });
  });
});

describe("validateUserMembership (token core)", () => {
  it("core cho phép: trả thông tin user, workspace và role", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    coreAllows(userId, orgId, "founder", "Validated Co");

    const result = await validateUserMembership({ platformToken: "opaque", companyId: orgId });

    expect(result).toMatchObject({
      valid: true,
      userId,
      companyId: orgId,
      companyName: "Validated Co",
      roleId: "founder",
      email: `wa-${userId}@core.test`,
    });
  });

  it("core từ chối -> permission_denied", async () => {
    coreAllows(generateSnowflakeStr(), generateSnowflakeStr());
    await expect(
      validateUserMembership({ platformToken: "opaque", companyId: generateSnowflakeStr() })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
