import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authorizeCoreOrganizationAction } from "../services/core-organization.service";

const CORE = "http://core.test";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("authorizeCoreOrganizationAction", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    process.env.CORE_BASE_URL = CORE;
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("chuyển tiếp bearer của user và trả role, membershipVersion", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        allowed: true,
        organizationId: "100",
        organizationName: "Acme",
        ownerUserId: "7",
        subjectId: "42",
        role: "founder",
        typeCode: null,
        membershipVersion: 4,
      })
    );

    const decision = await authorizeCoreOrganizationAction("tok-1", "100", "cosa.workspace.read");

    expect(decision).toEqual({
      role: "founder",
      membershipVersion: 4,
      typeCode: null,
      organizationName: "Acme",
      ownerUserId: "7",
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${CORE}/me/organizations/100/authorize`);
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok-1");
    expect(JSON.parse(init.body)).toEqual({ action: "cosa.workspace.read" });
  });

  it("mã hoá organizationId trong path", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ allowed: true, role: "member", membershipVersion: 1, organizationName: "A", ownerUserId: "1" })
    );
    await authorizeCoreOrganizationAction("tok", "a/b", "cosa.workspace.read");
    expect(fetchMock.mock.calls[0][0]).toBe(`${CORE}/me/organizations/a%2Fb/authorize`);
  });

  it("core 401 -> unauthenticated", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ code: "unauthenticated" }, 401));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "unauthenticated",
    });
  });

  it("core 403 hoặc 404 -> permission_denied", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ code: "permission_denied" }, 403));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "permission_denied",
    });
    fetchMock.mockResolvedValueOnce(jsonResponse({ code: "not_found" }, 404));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  it("core 5xx hoặc lỗi mạng -> unavailable", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 502));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "unavailable",
    });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "unavailable",
    });
  });

  it("allowed=false từ core -> permission_denied", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ allowed: false }));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  it("core thiếu tên hoặc chủ sở hữu organization -> unavailable (không tự đoán)", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ allowed: true, role: "member", membershipVersion: 1 }));
    await expect(authorizeCoreOrganizationAction("tok", "100", "cosa.workspace.read")).rejects.toMatchObject({
      code: "unavailable",
    });
  });
});
