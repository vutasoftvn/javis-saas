import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as coreOrganization from "../services/core-organization.service";
import { listCoreCompanies } from "../services/company.service";
import { listMyCompaniesFor } from "../handlers/company.handler";

describe("listCoreOrganizations", () => {
  const fetchMock = vi.fn();
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

  beforeEach(() => {
    process.env.CORE_BASE_URL = "http://core.test";
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("gọi GET /me/organizations bằng bearer của user", async () => {
    fetchMock.mockResolvedValueOnce(
      json({
        organizations: [
          { organizationId: "1", name: "A", role: "founder", isActive: true, isDefault: true },
        ],
      })
    );

    const result = await coreOrganization.listCoreOrganizations("tok-1");

    expect(result).toEqual([{ organizationId: "1", name: "A", role: "founder" }]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://core.test/me/organizations");
    expect(init.headers.Authorization).toBe("Bearer tok-1");
  });

  it("bỏ organization không active; 401 -> unauthenticated; 5xx hoặc mạng -> unavailable", async () => {
    fetchMock.mockResolvedValueOnce(
      json({
        organizations: [
          { organizationId: "1", name: "A", role: "member", isActive: true },
          { organizationId: "2", name: "B", role: "member", isActive: false },
        ],
      })
    );
    expect(await coreOrganization.listCoreOrganizations("t")).toHaveLength(1);

    fetchMock.mockResolvedValueOnce(json({}, 401));
    await expect(coreOrganization.listCoreOrganizations("t")).rejects.toMatchObject({ code: "unauthenticated" });
    fetchMock.mockResolvedValueOnce(json({}, 500));
    await expect(coreOrganization.listCoreOrganizations("t")).rejects.toMatchObject({ code: "unavailable" });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(coreOrganization.listCoreOrganizations("t")).rejects.toMatchObject({ code: "unavailable" });
  });
});

describe("listCoreCompanies / listMyCompaniesFor", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("quy role của core về role COSA và bỏ role không dùng được ở COSA", async () => {
    vi.spyOn(coreOrganization, "listCoreOrganizations").mockResolvedValue([
      { organizationId: "1", name: "Owned", role: "owner" },
      { organizationId: "2", name: "Viewer", role: "viewer" },
      { organizationId: "3", name: "Fleet", role: "driver" },
      { organizationId: "4", name: "Ops", role: "operator" },
    ]);

    const res = await listCoreCompanies("tok-1");

    expect(res.companies).toEqual([
      { company_id: "1", name: "Owned", role_id: "founder" },
      { company_id: "2", name: "Viewer", role_id: "viewer" },
    ]);
  });

  it("handler dùng core khi token là của core", async () => {
    const list = vi
      .spyOn(coreOrganization, "listCoreOrganizations")
      .mockResolvedValue([{ organizationId: "9", name: "Nine", role: "admin" }]);

    const res = await listMyCompaniesFor({ userID: "42", accessToken: "tok-9" });

    expect(list).toHaveBeenCalledWith("tok-9");
    expect(res.companies).toEqual([{ company_id: "9", name: "Nine", role_id: "admin" }]);
  });
});
