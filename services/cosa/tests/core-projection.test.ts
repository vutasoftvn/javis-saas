import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "../services/snowflake.service";
import { mapCoreRoleToCosaRole, projectCoreAccess, projectCoreUser } from "../services/core-projection.service";

const { users, profiles, workspaces, workspaceMemberships } = schema;

function ids() {
  return { userId: generateSnowflakeStr(), organizationId: generateSnowflakeStr(), ownerUserId: generateSnowflakeStr() };
}

describe("mapCoreRoleToCosaRole", () => {
  it("giữ role cosa, quy owner về founder, role giao thông về member", () => {
    expect(mapCoreRoleToCosaRole("founder")).toBe("founder");
    expect(mapCoreRoleToCosaRole("owner")).toBe("founder");
    expect(mapCoreRoleToCosaRole("co-founder")).toBe("co-founder");
    expect(mapCoreRoleToCosaRole("admin")).toBe("admin");
    expect(mapCoreRoleToCosaRole("viewer")).toBe("viewer");
    expect(mapCoreRoleToCosaRole("member")).toBe("member");
    expect(mapCoreRoleToCosaRole("operator")).toBe("member");
    expect(mapCoreRoleToCosaRole("driver")).toBe("member");
    expect(mapCoreRoleToCosaRole("something-else")).toBe("member");
  });
});

describe("projectCoreUser", () => {
  it("chỉ chiếu user và profile, chưa tạo workspace hay membership", async () => {
    const { userId } = ids();
    await projectCoreUser({ userId, email: `u-${userId}@core.test`, phone: null, displayName: "Solo", avatarUrl: null });

    const [u] = await db.select().from(users).where(eq(users.id, BigInt(userId)));
    expect(u.hashedPassword).toBeNull();
    const [p] = await db.select().from(profiles).where(eq(profiles.id, BigInt(userId)));
    expect(p.fullName).toBe("Solo");
    const members = await db.select().from(workspaceMemberships).where(eq(workspaceMemberships.userId, BigInt(userId)));
    expect(members).toHaveLength(0);
  });
});

describe("projectCoreAccess", () => {
  it("tạo user (không mật khẩu), profile, workspace và membership theo id của core", async () => {
    const { userId, organizationId, ownerUserId } = ids();

    await projectCoreAccess({
      user: { userId, email: `p-${userId}@core.test`, phone: null, displayName: "An Nguyen", avatarUrl: null },
      organization: { organizationId, name: "Acme", ownerUserId },
      role: "founder",
    });

    const [u] = await db.select().from(users).where(eq(users.id, BigInt(userId)));
    expect(u.email).toBe(`p-${userId}@core.test`);
    expect(u.hashedPassword).toBeNull();

    const [p] = await db.select().from(profiles).where(eq(profiles.id, BigInt(userId)));
    expect(p.fullName).toBe("An Nguyen");

    const [w] = await db.select().from(workspaces).where(eq(workspaces.id, BigInt(organizationId)));
    expect(w.workspaceName).toBe("Acme");
    expect(w.ownerId).toBe(BigInt(ownerUserId));

    const [m] = await db
      .select()
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.organizationId, BigInt(organizationId)), eq(workspaceMemberships.userId, BigInt(userId))));
    expect(m.roleId).toBe("founder");
  });

  it("idempotent và cập nhật role, tên, email khi core thay đổi", async () => {
    const { userId, organizationId, ownerUserId } = ids();
    const base = {
      user: { userId, email: `a-${userId}@core.test`, phone: null, displayName: "Old", avatarUrl: null },
      organization: { organizationId, name: "Old Name", ownerUserId },
    };
    await projectCoreAccess({ ...base, role: "member" });
    await projectCoreAccess({
      user: { ...base.user, email: `b-${userId}@core.test`, displayName: "New" },
      organization: { ...base.organization, name: "New Name" },
      role: "admin",
    });

    const [u] = await db.select().from(users).where(eq(users.id, BigInt(userId)));
    expect(u.email).toBe(`b-${userId}@core.test`);
    const [p] = await db.select().from(profiles).where(eq(profiles.id, BigInt(userId)));
    expect(p.fullName).toBe("New");
    const [w] = await db.select().from(workspaces).where(eq(workspaces.id, BigInt(organizationId)));
    expect(w.workspaceName).toBe("New Name");
    const members = await db
      .select()
      .from(workspaceMemberships)
      .where(eq(workspaceMemberships.organizationId, BigInt(organizationId)));
    expect(members).toHaveLength(1);
    expect(members[0].roleId).toBe("admin");
  });

  it("không ghi đè locale ưa thích của người dùng", async () => {
    const { userId, organizationId, ownerUserId } = ids();
    const input = {
      user: { userId, email: `l-${userId}@core.test`, phone: null, displayName: "L", avatarUrl: null },
      organization: { organizationId, name: "Locale Co", ownerUserId },
      role: "member",
    };
    await projectCoreAccess(input);
    await db.update(profiles).set({ preferredLocale: "en-US" }).where(eq(profiles.id, BigInt(userId)));
    await projectCoreAccess(input);

    const [p] = await db.select().from(profiles).where(eq(profiles.id, BigInt(userId)));
    expect(p.preferredLocale).toBe("en-US");
  });

  it("user chỉ có số điện thoại vẫn chiếu được; không có cả hai thì dùng email giữ chỗ", async () => {
    const a = ids();
    await projectCoreAccess({
      user: { userId: a.userId, email: null, phone: `+84${a.userId.slice(-9)}`, displayName: null, avatarUrl: null },
      organization: { organizationId: a.organizationId, name: "Phone Co", ownerUserId: a.ownerUserId },
      role: "member",
    });
    const [ua] = await db.select().from(users).where(eq(users.id, BigInt(a.userId)));
    expect(ua.email).toBeNull();
    expect(ua.phone).toBe(`+84${a.userId.slice(-9)}`);

    const b = ids();
    await projectCoreAccess({
      user: { userId: b.userId, email: null, phone: null, displayName: null, avatarUrl: null },
      organization: { organizationId: b.organizationId, name: "Nobody Co", ownerUserId: b.ownerUserId },
      role: "member",
    });
    const [ub] = await db.select().from(users).where(eq(users.id, BigInt(b.userId)));
    expect(ub.email).toBe(`user-${b.userId}@core.invalid`);
  });
});
