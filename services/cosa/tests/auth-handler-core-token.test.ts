import { beforeEach, describe, expect, it, vi } from "vitest";
import { resolveBearerAuthData } from "../handlers/auth.handler";
import * as coreIntrospect from "../services/core-introspect.service";
import * as coreProjection from "../services/core-projection.service";

const info = {
  userId: "42",
  clientId: "vn.mivacorp.cosa",
  scopes: ["openid"],
  expiresAt: 9999999999,
  email: "a@b.vn",
  phone: null,
  displayName: "An",
  avatarUrl: null,
};

describe("resolveBearerAuthData", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("thiếu hoặc sai định dạng Authorization -> unauthenticated", async () => {
    await expect(resolveBearerAuthData(undefined)).rejects.toMatchObject({ code: "unauthenticated" });
    await expect(resolveBearerAuthData("Basic abc")).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("token dạng JWT không phải danh tính người dùng -> unauthenticated, không gọi core", async () => {
    const introspect = vi.spyOn(coreIntrospect, "introspectCoreToken");

    await expect(resolveBearerAuthData("Bearer aaa.bbb.ccc")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(introspect).not.toHaveBeenCalled();
  });

  it("token opaque của core: introspect, chiếu user, trả userID của core kèm access token", async () => {
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockResolvedValue(info);
    const project = vi.spyOn(coreProjection, "projectCoreUser").mockResolvedValue();

    const data = await resolveBearerAuthData("Bearer opaque-token");

    expect(data).toEqual({ userID: "42", accessToken: "opaque-token" });
    expect(project).toHaveBeenCalledWith({
      userId: "42",
      email: "a@b.vn",
      phone: null,
      displayName: "An",
      avatarUrl: null,
    });
  });

  it("token core bị từ chối -> lỗi nổi lên, không chiếu user", async () => {
    vi.spyOn(coreIntrospect, "introspectCoreToken").mockRejectedValue(
      Object.assign(new Error("invalid"), { code: "unauthenticated" })
    );
    const project = vi.spyOn(coreProjection, "projectCoreUser");

    await expect(resolveBearerAuthData("Bearer opaque-token")).rejects.toMatchObject({ code: "unauthenticated" });
    expect(project).not.toHaveBeenCalled();
  });
});
