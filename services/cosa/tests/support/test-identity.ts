import { and, eq } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflakeStr } from "../../services/snowflake.service";
import { projectCoreUser } from "../../services/core-projection.service";
import { provisionVentureWorkspace } from "../../services/venture-workspace.service";

/**
 * Core giả cho test COSA. Danh tính và quyền do backend/core quyết định, nên test không còn tự đăng ký
 * user hay ký token platform: token test là chuỗi opaque `fc_<userId>` và `fakeCoreFetch` trả lời các
 * endpoint của core (introspect, authorize, danh sách/tạo organization, cấp membership) dựa trên DB test
 * của COSA (bản chiếu membership) cộng với các thay đổi "ở core" trong bộ nhớ.
 */

const { users, profiles, workspaces, workspaceMemberships } = schema;

export const FAKE_CORE_BASE_URL = "http://fake-core.test";

interface ExtraMembership {
  role: string;
  organizationName: string;
  ownerUserId: string;
}

// Thay đổi "ở core" (tạo organization, cấp membership) chưa có trong DB COSA: `${orgId}:${userId}`.
const extraMemberships = new Map<string, ExtraMembership>();

// Khi được đặt, MỌI user đều là thành viên MỌI organization với role này (mô phỏng "caller có role X").
let defaultRole: string | null = null;

export function setFakeCoreDefaultMembership(role: string | null): void {
  defaultRole = role;
}

/** Id số ổn định cho một nhãn test (user/workspace symbolic), vì id của core là snowflake bigint. */
export function stableId(label: string): string {
  let h = 5381n;
  for (const ch of label) h = (h * 33n + BigInt(ch.charCodeAt(0))) % 900000000000000n;
  return (100000000000000n + h).toString();
}

export function fakeCoreToken(userId: string): string {
  return `fc_${userId}`;
}

export function userIdOfFakeToken(token: string): string | null {
  const bare = token.replace(/^Bearer\s+/i, "");
  return bare.startsWith("fc_") ? bare.slice(3) : null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

async function membershipOf(userId: string, orgId: string): Promise<ExtraMembership | null> {
  const extra = extraMemberships.get(`${orgId}:${userId}`);
  if (extra) return extra;
  if (defaultRole) return { role: defaultRole, organizationName: "Fake Org", ownerUserId: userId };
  if (!/^\d+$/.test(userId) || !/^\d+$/.test(orgId)) return null;
  const [row] = await db
    .select({
      role: workspaceMemberships.roleId,
      name: workspaces.workspaceName,
      ownerId: workspaces.ownerId,
      status: workspaces.status,
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .where(and(eq(workspaceMemberships.userId, BigInt(userId)), eq(workspaceMemberships.workspaceId, BigInt(orgId))))
    .limit(1);
  if (!row || row.status !== "active") return null;
  return { role: row.role, organizationName: row.name, ownerUserId: row.ownerId.toString() };
}

async function orgsOf(userId: string): Promise<Array<{ organizationId: string } & ExtraMembership>> {
  const result = new Map<string, { organizationId: string } & ExtraMembership>();
  if (/^\d+$/.test(userId)) {
    const rows = await db
      .select({
        orgId: workspaces.id,
        role: workspaceMemberships.roleId,
        name: workspaces.workspaceName,
        ownerId: workspaces.ownerId,
        status: workspaces.status,
      })
      .from(workspaceMemberships)
      .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
      .where(eq(workspaceMemberships.userId, BigInt(userId)));
    for (const r of rows) {
      if (r.status !== "active") continue;
      result.set(r.orgId.toString(), {
        organizationId: r.orgId.toString(),
        role: r.role,
        organizationName: r.name,
        ownerUserId: r.ownerId.toString(),
      });
    }
  }
  for (const [key, value] of extraMemberships) {
    const [orgId, uid] = key.split(":");
    if (uid === userId) result.set(orgId, { organizationId: orgId, ...value });
  }
  return [...result.values()];
}

async function dbUser(userId: string) {
  if (!/^\d+$/.test(userId)) return null;
  const [row] = await db
    .select({ email: users.email, phone: users.phone, name: profiles.fullName, avatar: profiles.avatarUrl })
    .from(users)
    .leftJoin(profiles, eq(profiles.id, users.id))
    .where(eq(users.id, BigInt(userId)))
    .limit(1);
  return row ?? null;
}

export async function fakeCoreFetch(input: unknown, init?: RequestInit): Promise<Response> {
  const url = new URL(typeof input === "string" ? input : (input as URL | Request).toString());
  if (!input || !String(input).startsWith(FAKE_CORE_BASE_URL)) {
    throw new Error(`unexpected network call in test: ${String(input)}`);
  }
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers as HeadersInit | undefined);
  const bearerUser = userIdOfFakeToken(headers.get("authorization") ?? "");
  const body = init?.body ? JSON.parse(String(init.body)) : {};
  const path = url.pathname;

  if (method === "POST" && path === "/oauth/introspect") {
    const uid = userIdOfFakeToken(String(body.token ?? ""));
    if (!uid) return json({ active: false });
    const u = await dbUser(uid);
    return json({
      active: true,
      userId: uid,
      email: u?.email ?? `fc-${uid}@core.test`,
      phone: u?.phone ?? null,
      displayName: u?.name ?? "Fake User",
      avatarUrl: u?.avatar ?? null,
      clientId: "1",
      clientPublicId: "vn.mivacorp.cosa",
      scope: "openid profile email",
      exp: Math.floor(Date.now() / 1000) + 3600,
    });
  }

  const authorize = /^\/me\/organizations\/([^/]+)\/authorize$/.exec(path);
  if (method === "POST" && authorize) {
    if (!bearerUser) return json({ code: "unauthenticated" }, 401);
    const orgId = decodeURIComponent(authorize[1]);
    const m = await membershipOf(bearerUser, orgId);
    if (!m) return json({ code: "permission_denied" }, 403);
    return json({
      allowed: true,
      organizationId: orgId,
      organizationName: m.organizationName,
      ownerUserId: m.ownerUserId,
      subjectId: bearerUser,
      role: m.role,
      typeCode: null,
      membershipVersion: 1,
    });
  }

  if (method === "GET" && path === "/me/organizations") {
    if (!bearerUser) return json({ code: "unauthenticated" }, 401);
    const orgs = await orgsOf(bearerUser);
    return json({
      organizations: orgs.map((o) => ({
        organizationId: o.organizationId,
        name: o.organizationName,
        role: o.role,
        isActive: true,
        isDefault: false,
      })),
    });
  }

  if (method === "POST" && path === "/companies") {
    if (!bearerUser) return json({ code: "unauthenticated" }, 401);
    const id = generateSnowflakeStr();
    extraMemberships.set(`${id}:${bearerUser}`, {
      role: body.creatorRole ?? "owner",
      organizationName: body.name,
      ownerUserId: bearerUser,
    });
    return json({ id, name: body.name, userId: bearerUser, legalStatus: "unregistered" });
  }

  const grant = /^\/internal\/organizations\/([^/]+)\/members$/.exec(path);
  if (method === "POST" && grant) {
    const orgId = decodeURIComponent(grant[1]);
    const existing = await membershipOf(String(body.userId), orgId);
    if (existing) return json({ role: existing.role, membershipVersion: 1 });
    const [ws] = /^\d+$/.test(orgId)
      ? await db.select().from(workspaces).where(eq(workspaces.id, BigInt(orgId))).limit(1)
      : [];
    if (!ws) return json({ code: "not_found" }, 404);
    extraMemberships.set(`${orgId}:${body.userId}`, {
      role: body.role,
      organizationName: ws.workspaceName,
      ownerUserId: ws.ownerId.toString(),
    });
    return json({ role: body.role, membershipVersion: 1 });
  }

  return json({ code: "not_found", message: `fake core: ${method} ${path}` }, 404);
}

export function resetFakeCore(): void {
  extraMemberships.clear();
  defaultRole = null;
}

export interface TestUserParams {
  email?: string;
  password?: string;
  full_name?: string;
  phone?: string;
  workspace_name?: string;
  company_name?: string; // alias của workspace_name
  client_workspace_creation_id?: string;
  preferred_locale?: string;
}

export interface TestUserResult {
  access_token: string;
  token_type: string;
  user: { id: string; email: string | null; phone: string | null; full_name: string | null; preferred_locale: string };
  platform_workspace_id?: string;
}

/**
 * Tạo user (bản chiếu từ core), tuỳ chọn kèm workspace, và trả token của core giả. Thay cho
 * `registerPlatformUser` cũ (đăng ký cục bộ đã được gỡ; đăng ký do backend/core quản lý).
 */
export async function registerTestUser(params: TestUserParams = {}): Promise<TestUserResult> {
  const userId = generateSnowflakeStr();
  const email = params.email ?? `test-${userId}@core.test`;
  await projectCoreUser({ userId, email, phone: params.phone ?? null, displayName: params.full_name ?? null });
  if (params.preferred_locale) {
    await db
      .update(profiles)
      .set({ preferredLocale: params.preferred_locale })
      .where(eq(profiles.id, BigInt(userId)));
  }

  let workspaceId: string | undefined;
  const workspaceName = params.workspace_name ?? params.company_name;
  if (workspaceName) {
    const res = await provisionVentureWorkspace({
      ownerUserId: BigInt(userId),
      workspaceName,
      clientCreationId: params.client_workspace_creation_id ?? `test-ws-${userId}`,
    });
    workspaceId = res.platformWorkspaceId;
    // Như createNewCompany: người tạo workspace được nâng profile role lên founder.
    await db
      .update(profiles)
      .set({ roleId: "founder" })
      .where(and(eq(profiles.id, BigInt(userId)), eq(profiles.roleId, "member")));
  }

  return {
    access_token: fakeCoreToken(userId),
    token_type: "bearer",
    user: {
      id: userId,
      email,
      phone: params.phone ?? null,
      full_name: params.full_name ?? null,
      preferred_locale: params.preferred_locale ?? "vi-VN",
    },
    platform_workspace_id: workspaceId,
  };
}

// Tên cũ giữ nguyên để các test không phải đổi thân test.
export const registerPlatformUser = registerTestUser;
export const registerPlatform = registerTestUser;

/** Người giữ token của core giả (thay cho `verifyPlatformToken(token).sub`). */
export function verifyPlatformToken(token: string): { sub: string; aud: "cosa" } {
  const uid = userIdOfFakeToken(token);
  if (!uid) throw new Error("not a fake core token");
  return { sub: uid, aud: "cosa" };
}

/** Token của core giả cho một user id (thay cho `signPlatformToken`). */
export function signPlatformToken(userId: string): string {
  return fakeCoreToken(userId);
}

/** AuthData của Gateway cho handler gọi trực tiếp trong test. */
export function asCaller(userId: string): { userID: string; accessToken: string } {
  return { userID: userId, accessToken: fakeCoreToken(userId) };
}
