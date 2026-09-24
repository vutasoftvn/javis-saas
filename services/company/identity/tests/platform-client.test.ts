import { describe, it, expect, afterEach } from "vitest";
import { getPlatformUrl } from "../services/platform.client";

describe("platform.client configuration errors", () => {
  const prevUrl = process.env.PLATFORM_API_BASE_URL;
  const prevEnv = process.env.NODE_ENV;

  afterEach(() => {
    if (prevUrl === undefined) delete process.env.PLATFORM_API_BASE_URL;
    else process.env.PLATFORM_API_BASE_URL = prevUrl;
    if (prevEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = prevEnv;
  });

  it("throws APIError.internal when PLATFORM_API_BASE_URL uses dev default in prod", () => {
    process.env.NODE_ENV = "production";
    process.env.PLATFORM_API_BASE_URL = "http://127.0.0.1:4001";

    expect(() => getPlatformUrl()).toThrow(
      expect.objectContaining({ code: "internal" })
    );
  });
});

import { vi, beforeEach } from "vitest";
import {
  listPlatformWorkspaceMemberships,
  resolvePlatformIdentity,
  validatePlatformWorkspaceMembership,
} from "../services/platform.client";

describe("platform.client với access token OIDC của core (token opaque)", () => {
  const fetchMock = vi.fn();
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("resolvePlatformIdentity: token opaque hỏi control-plane (cosa) và trả userId", async () => {
    fetchMock.mockResolvedValueOnce(json({ userId: "42", email: "a@b.vn", displayName: "An" }));

    const identity = await resolvePlatformIdentity("opaque-token");

    expect(identity).toEqual({ userId: "42", email: "a@b.vn", displayName: "An" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/platform\/internal\/resolve-identity$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ platformToken: "opaque-token" });
  });

  it("resolvePlatformIdentity: token dạng JWT không phải danh tính người dùng -> unauthenticated, không gọi mạng", async () => {
    await expect(resolvePlatformIdentity("aaa.bbb.ccc")).rejects.toMatchObject({ code: "unauthenticated" });
    await expect(resolvePlatformIdentity("")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("resolvePlatformIdentity: cosa 401 -> unauthenticated, 5xx hoặc mạng -> unavailable", async () => {
    fetchMock.mockResolvedValueOnce(json({}, 401));
    await expect(resolvePlatformIdentity("opaque")).rejects.toMatchObject({ code: "unauthenticated" });
    fetchMock.mockResolvedValueOnce(json({}, 503));
    await expect(resolvePlatformIdentity("opaque")).rejects.toMatchObject({ code: "unavailable" });
    fetchMock.mockRejectedValueOnce(new Error("ECONNRESET"));
    await expect(resolvePlatformIdentity("opaque")).rejects.toMatchObject({ code: "unavailable" });
  });

  it("list và validate membership không verify cục bộ token opaque", async () => {
    fetchMock.mockResolvedValueOnce(json({ memberships: [] }));
    expect(await listPlatformWorkspaceMemberships({ platformToken: "opaque" })).toEqual([]);

    fetchMock.mockResolvedValueOnce(
      json({ valid: true, membership: { platformWorkspaceId: "9", userId: "42", role: "founder" } })
    );
    const res = await validatePlatformWorkspaceMembership({ platformToken: "opaque", platformWorkspaceId: "9" });
    expect(res).toMatchObject({ valid: true, platformWorkspaceId: "9" });
  });
});
