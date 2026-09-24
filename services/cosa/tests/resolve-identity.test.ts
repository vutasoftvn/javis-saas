import { afterEach, describe, expect, it, vi } from "vitest";
import { generateSnowflakeStr } from "../services/snowflake.service";
import * as coreIntrospect from "../services/core-introspect.service";
import { resolveIdentityForToken } from "../services/workspace-access.service";
import { resolveIdentityEndpoint } from "../handlers/venture-workspace.handler";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("resolveIdentityForToken", () => {
  it("token core: trả id, email, tên hiển thị đã chiếu", async () => {
    const userId = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue({
      userId,
      clientId: "vn.mivacorp.cosa",
      scopes: [],
      expiresAt: 9999999999,
      email: `id-${userId}@core.test`,
      displayName: "Ident Tity",
    });

    expect(await resolveIdentityForToken("opaque")).toEqual({
      userId,
      email: `id-${userId}@core.test`,
      displayName: "Ident Tity",
    });
  });

  it("token dạng JWT không phải danh tính người dùng -> unauthenticated", async () => {
    await expect(resolveIdentityForToken("aaa.bbb.ccc")).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

describe("resolveIdentityEndpoint", () => {
  it("nhận platformToken trong body và trả danh tính", async () => {
    const userId = generateSnowflakeStr();
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue({
      userId,
      clientId: "vn.mivacorp.cosa",
      scopes: [],
      expiresAt: 9999999999,
      email: `ep-${userId}@core.test`,
      displayName: "Endpoint",
    });

    const res = await resolveIdentityEndpoint({ platformToken: "opaque" });

    expect(res.userId).toBe(userId);
  });
});
