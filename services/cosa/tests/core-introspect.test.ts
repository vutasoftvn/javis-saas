import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearIntrospectCache,
  introspectCoreToken,
} from "../services/core-introspect.service";

const CORE = "http://core.test";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

const activeBody = (over: Record<string, unknown> = {}) => ({
  active: true,
  userId: "42",
  email: "a@b.vn",
  displayName: "An",
  clientId: "7",
  clientPublicId: "vn.mivacorp.cosa",
  scope: "openid profile email",
  exp: Math.floor(Date.now() / 1000) + 600,
  ...over,
});

describe("introspectCoreToken", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    process.env.CORE_BASE_URL = CORE;
    process.env.CORE_INTROSPECT_CLIENT_ID = "vn.mivacorp.cosa.backend";
    process.env.CORE_INTROSPECT_CLIENT_SECRET = "s3cret";
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    clearIntrospectCache();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("trả thông tin token hợp lệ của client COSA", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody()));

    const info = await introspectCoreToken("tok-1");

    expect(info).toMatchObject({
      userId: "42",
      clientId: "vn.mivacorp.cosa",
      scopes: ["openid", "profile", "email"],
      email: "a@b.vn",
      displayName: "An",
    });
    expect(typeof info.expiresAt).toBe("number");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${CORE}/oauth/introspect`);
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe(
      "Basic " + Buffer.from("vn.mivacorp.cosa.backend:s3cret").toString("base64")
    );
    expect(JSON.parse(init.body)).toEqual({ token: "tok-1" });
  });

  it("chuyển role hệ thống (tầng A) của tài khoản; thiếu hoặc sai kiểu thì bỏ qua", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody({ systemRoles: ["user", "auditor"] })));
    expect((await introspectCoreToken("tok-a")).systemRoles).toEqual(["user", "auditor"]);

    clearIntrospectCache();
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody()));
    expect((await introspectCoreToken("tok-b")).systemRoles).toBeUndefined();

    clearIntrospectCache();
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody({ systemRoles: "user" as never })));
    expect((await introspectCoreToken("tok-c")).systemRoles).toBeUndefined();
  });

  it("token inactive -> unauthenticated", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ active: false }));
    await expect(introspectCoreToken("tok-2")).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("token của client khác hoặc thiếu clientPublicId -> unauthenticated", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody({ clientPublicId: "vn.mivacorp.id" })));
    await expect(introspectCoreToken("tok-3")).rejects.toMatchObject({ code: "unauthenticated" });
    fetchMock.mockResolvedValueOnce(jsonResponse(activeBody({ clientPublicId: undefined })));
    await expect(introspectCoreToken("tok-4")).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("token rỗng -> unauthenticated, không gọi core", async () => {
    await expect(introspectCoreToken("")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("core 5xx hoặc lỗi mạng -> unavailable (không nuốt thành unauthenticated)", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ code: "internal" }, 503));
    await expect(introspectCoreToken("tok-5")).rejects.toMatchObject({ code: "unavailable" });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(introspectCoreToken("tok-6")).rejects.toMatchObject({ code: "unavailable" });
  });

  it("core từ chối credential của COSA (401/403) -> internal, không phải lỗi của user", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ code: "unauthenticated" }, 401));
    await expect(introspectCoreToken("tok-7")).rejects.toMatchObject({ code: "internal" });
  });

  it("thiếu CORE_INTROSPECT_CLIENT_SECRET -> lỗi cấu hình, không gọi core", async () => {
    delete process.env.CORE_INTROSPECT_CLIENT_SECRET;
    await expect(introspectCoreToken("tok-8")).rejects.toThrow(/CORE_INTROSPECT_CLIENT_SECRET/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("cache kết quả active trong tối đa 30s rồi hỏi lại core", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-24T10:00:00Z"));
    const exp = Math.floor(Date.now() / 1000) + 600;
    fetchMock.mockImplementation(async () => jsonResponse(activeBody({ exp })));

    await introspectCoreToken("tok-9");
    await introspectCoreToken("tok-9");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    vi.setSystemTime(new Date("2026-09-24T10:00:31Z"));
    await introspectCoreToken("tok-9");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("không cache quá thời điểm token hết hạn", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-24T10:00:00Z"));
    const exp = Math.floor(Date.now() / 1000) + 5;
    fetchMock.mockImplementation(async () => jsonResponse(activeBody({ exp })));

    await introspectCoreToken("tok-10");
    vi.setSystemTime(new Date("2026-09-24T10:00:06Z"));
    await introspectCoreToken("tok-10");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("không cache kết quả inactive", async () => {
    fetchMock.mockImplementation(async () => jsonResponse({ active: false }));
    await expect(introspectCoreToken("tok-11")).rejects.toMatchObject({ code: "unauthenticated" });
    await expect(introspectCoreToken("tok-11")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
