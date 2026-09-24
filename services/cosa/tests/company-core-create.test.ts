import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreOrganization from "../services/core-organization.service";
import { projectCoreUser } from "../services/core-projection.service";
import { createNewCompany } from "../services/company.service";

const { workspaces, workspaceMemberships, workspaceLicenses, workspaceEntitlements } = schema;

describe("createCoreOrganization", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    process.env.CORE_BASE_URL = "http://core.test";
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

  it("gọi POST /companies bằng bearer của user, tạo organization chưa đăng ký với người tạo là founder", async () => {
    fetchMock.mockResolvedValueOnce(json({ id: "900", name: "Acme", legalStatus: "unregistered" }));

    const result = await coreOrganization.createCoreOrganization("tok-1", "Acme");

    expect(result).toEqual({ organizationId: "900", name: "Acme" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://core.test/companies");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok-1");
    expect(JSON.parse(init.body)).toEqual({ name: "Acme", creatorRole: "founder" });
  });

  it("401 -> unauthenticated, 400 -> invalid_argument, 5xx hoặc lỗi mạng -> unavailable", async () => {
    fetchMock.mockResolvedValueOnce(json({ code: "unauthenticated" }, 401));
    await expect(coreOrganization.createCoreOrganization("t", "A")).rejects.toMatchObject({ code: "unauthenticated" });
    fetchMock.mockResolvedValueOnce(json({ code: "invalid_argument" }, 400));
    await expect(coreOrganization.createCoreOrganization("t", "A")).rejects.toMatchObject({ code: "invalid_argument" });
    fetchMock.mockResolvedValueOnce(json({}, 503));
    await expect(coreOrganization.createCoreOrganization("t", "A")).rejects.toMatchObject({ code: "unavailable" });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(coreOrganization.createCoreOrganization("t", "A")).rejects.toMatchObject({ code: "unavailable" });
  });
});

describe("createNewCompany với access token của core", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("tạo organization ở core rồi dựng dữ liệu vận hành COSA với đúng id của core", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    await projectCoreUser({ userId, email: `c-${userId}@core.test`, displayName: "Creator" });
    const create = vi
      .spyOn(coreOrganization, "createCoreOrganization")
      .mockResolvedValue({ organizationId: orgId, name: "Core Made Co" });

    const res = await createNewCompany(userId, { name: "Core Made Co" }, { accessToken: "tok-1" });

    expect(create).toHaveBeenCalledWith("tok-1", "Core Made Co");
    expect(res).toMatchObject({ company_id: orgId, name: "Core Made Co", role_id: "founder" });

    const [ws] = await db.select().from(workspaces).where(eq(workspaces.id, BigInt(orgId)));
    expect(ws.workspaceName).toBe("Core Made Co");
    expect(ws.ownerId).toBe(BigInt(userId));
    const [mem] = await db.select().from(workspaceMemberships).where(eq(workspaceMemberships.workspaceId, BigInt(orgId)));
    expect(mem.roleId).toBe("founder");
    expect(mem.userId).toBe(BigInt(userId));
    const lic = await db.select().from(workspaceLicenses).where(eq(workspaceLicenses.workspaceId, BigInt(orgId)));
    expect(lic).toHaveLength(1);
    const ent = await db.select().from(workspaceEntitlements).where(eq(workspaceEntitlements.workspaceId, BigInt(orgId)));
    expect(ent).toHaveLength(1);
  });

  it("chịu được việc bản chiếu đã có workspace và membership (không lỗi trùng khoá)", async () => {
    const userId = generateSnowflakeStr();
    const orgId = generateSnowflakeStr();
    await projectCoreUser({ userId, email: `d-${userId}@core.test`, displayName: "Creator" });
    const { projectCoreAccess } = await import("../services/core-projection.service");
    await projectCoreAccess({
      user: { userId, email: `d-${userId}@core.test`, displayName: "Creator" },
      organization: { organizationId: orgId, name: "Pre Projected", ownerUserId: userId },
      role: "founder",
    });
    vi.spyOn(coreOrganization, "createCoreOrganization").mockResolvedValue({ organizationId: orgId, name: "Pre Projected" });

    const res = await createNewCompany(userId, { name: "Pre Projected" }, { accessToken: "tok-1" });

    expect(res.company_id).toBe(orgId);
    const members = await db.select().from(workspaceMemberships).where(eq(workspaceMemberships.workspaceId, BigInt(orgId)));
    expect(members).toHaveLength(1);
  });

  it("core từ chối thì không tạo gì ở COSA", async () => {
    const userId = generateSnowflakeStr();
    await projectCoreUser({ userId, email: `e-${userId}@core.test` });
    vi.spyOn(coreOrganization, "createCoreOrganization").mockRejectedValue(
      Object.assign(new Error("down"), { code: "unavailable" })
    );

    await expect(createNewCompany(userId, { name: "Never Created" }, { accessToken: "tok-1" })).rejects.toMatchObject({
      code: "unavailable",
    });
    const members = await db.select().from(workspaceMemberships).where(eq(workspaceMemberships.userId, BigInt(userId)));
    expect(members).toHaveLength(0);
  });

  it("tên rỗng bị từ chối trước khi gọi core", async () => {
    const create = vi.spyOn(coreOrganization, "createCoreOrganization");
    await expect(createNewCompany("1", { name: "  " }, { accessToken: "tok" })).rejects.toMatchObject({
      code: "invalid_argument",
    });
    expect(create).not.toHaveBeenCalled();
  });
});
