import { afterEach, describe, expect, it, vi } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreIntrospect from "../services/core-introspect.service";
import * as coreOrganization from "../services/core-organization.service";
import {
  authorizeAndProjectCoreAccess,
  resolveCallerIdentity,
  syncCoreMembershipsForUser,
} from "../services/core-access.service";

const info = (userId: string) => ({
  userId,
  clientId: "vn.mivacorp.cosa",
  scopes: ["openid"],
  expiresAt: 9999999999,
  email: `u-${userId}@core.test`,
  displayName: "Tester",
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("resolveCallerIdentity", () => {
  it("token dạng JWT không phải danh tính người dùng: từ chối, không gọi core", async () => {
    const introspect = vi.spyOn(coreIntrospect, "introspectCoreToken");

    await expect(resolveCallerIdentity("aaa.bbb.ccc")).rejects.toMatchObject({ code: "unauthenticated" });
    await expect(resolveCallerIdentity("")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(introspect).not.toHaveBeenCalled();
  });

  it("token opaque của core: introspect và chiếu user", async () => {
    const userId = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));

    const caller = await resolveCallerIdentity("opaque-token");

    expect(caller).toEqual({ userId, accessToken: "opaque-token" });
    const [u] = await db.select().from(schema.users).where(eq(schema.users.id, BigInt(userId)));
    expect(u.hashedPassword).toBeNull();
  });
});

describe("authorizeAndProjectCoreAccess", () => {
  it("core cho phép: chiếu user, organization, role và trả quyết định", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    const ownerId = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));
    vi.spyOn(coreOrganization, "authorizeCoreOrganizationAction").mockResolvedValue({
      role: "admin",
      membershipVersion: 3,
      typeCode: null,
      organizationName: "Projected Co",
      ownerUserId: ownerId,
    });

    const access = await authorizeAndProjectCoreAccess("opaque", orgId, "cosa.workspace.read");

    expect(access).toMatchObject({ userId, role: "admin", cosaRole: "admin", membershipVersion: 3 });
    const [m] = await db
      .select()
      .from(schema.workspaceMemberships)
      .where(eq(schema.workspaceMemberships.organizationId, BigInt(orgId)));
    expect(m.roleId).toBe("admin");
  });

  it("core từ chối: không chiếu gì", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));
    vi.spyOn(coreOrganization, "authorizeCoreOrganizationAction").mockRejectedValue(
      Object.assign(new Error("no"), { code: "permission_denied" })
    );

    await expect(authorizeAndProjectCoreAccess("opaque", orgId, "cosa.workspace.read")).rejects.toMatchObject({
      code: "permission_denied",
    });
    const rows = await db.select().from(schema.workspaces).where(eq(schema.workspaces.id, BigInt(orgId)));
    expect(rows).toHaveLength(0);
  });
});

describe("syncCoreMembershipsForUser", () => {
  it("chiếu mọi organization COSA của user từ core và trả về danh sách id", async () => {
    const userId = generateSnowflakeStr();
    const org1 = generateSnowflakeStr();
    const org2 = generateSnowflakeStr();
    const fleet = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info(userId));
    vi.spyOn(coreOrganization, "listCoreOrganizations").mockResolvedValue([
      { organizationId: org1, name: "One", role: "founder" },
      { organizationId: org2, name: "Two", role: "viewer" },
      { organizationId: fleet, name: "Fleet", role: "driver" },
    ]);
    const authorize = vi.spyOn(coreOrganization, "authorizeCoreOrganizationAction").mockImplementation(
      async (_t, organizationId) => ({
        role: organizationId === org1 ? "founder" : "viewer",
        membershipVersion: 1,
        typeCode: null,
        organizationName: organizationId === org1 ? "One" : "Two",
        ownerUserId: userId,
      })
    );

    const ids = await syncCoreMembershipsForUser("opaque");

    expect(ids.sort()).toEqual([org1, org2].sort());
    expect(authorize).toHaveBeenCalledTimes(2);
    const members = await db
      .select()
      .from(schema.workspaceMemberships)
      .where(eq(schema.workspaceMemberships.userId, BigInt(userId)));
    expect(members).toHaveLength(2);
  });
});
